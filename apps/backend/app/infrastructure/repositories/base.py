import json
import logging
from functools import cache

from sqlalchemy import and_, asc, create_engine, desc, false, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from common.exceptions import BrokerError, ConflictError, InvalidFilterError, NotFoundError
from common.metrics import BROKER_COMMANDS
from common.tenant_context import get_current_tenant
from config.settings import settings
from infrastructure.exceptions import DBReposException

logger = logging.getLogger(__name__)

# Seconds to wait for the broker to acknowledge a command before treating it as failed.
BROKER_DELIVERY_TIMEOUT_SECONDS = 5


def engine_options(uri: str) -> dict:
    """
    Pool sizing and timeouts for a database URI. Postgres gets a connect timeout and a
    server-side statement timeout on every connection (settings.DATABASE); SQLite (tests) gets
    neither, it has no such knobs.
    """
    if not uri.startswith("postgresql"):
        return {}
    db = settings.DATABASE
    return {
        "pool_size": 10,
        "max_overflow": 20,
        "connect_args": {
            "connect_timeout": db.CONNECT_TIMEOUT_SECONDS,
            "options": f"-c statement_timeout={db.STATEMENT_TIMEOUT_MS}",
        },
    }


class BaseDBRepo:
    """
    BaseDBRepo is an Abstract Class
    """

    MODEL = None
    ENTITY = None
    ADAPTOR = None
    READ_ONLY_FIELDS = ["id", "created_date"]
    TENANT_SCOPE = None  # a TenantScope (repositories/tenancy.py), or None: no farm linkage

    def __init__(self, uri: str, echo: bool = False):
        """
        Initialize Repo with database URI and debug mode.
        logic:
            1- Get Engine
            2- Create a session maker
        @param uri: Database URI.
        @type uri: str
        @param echo: Debug mode.
        @type echo: bool
        """
        self.engine = self.get_engine(uri, echo)
        self.Session = sessionmaker(bind=self.engine)

    @staticmethod
    @cache
    def get_engine(uri: str, echo: bool = False):
        """
        Get the SQLAlchemy engine, one per URI for the whole process (every repository shares
        the same connection pool instead of opening one pool per repository class).

        @param uri: Database URI.
        @type uri: str
        @param echo: Debug mode.
        @type echo: bool

        @return: SQLAlchemy engine.
        @rtype: sqlalchemy.engine.base.Engine
        """
        try:
            # The API threadpool runs up to 40 sync handlers at once; the default pool (5 + 10)
            # would make a burst above 15 wait up to pool_timeout. pool_recycle drops connections
            # before a proxy or Postgres idle timeout can, pool_pre_ping catches the rest.
            return create_engine(uri, echo=echo, pool_pre_ping=True, pool_recycle=1800, **engine_options(uri))
        except Exception as e:
            raise DBReposException(f"Error creating engine: {e}") from e

    # ---- tenancy -------------------------------------------------------------------------

    def _apply_tenant(self, query, session):
        """
        Restrict a query to the caller's farm, per this repo's TENANT_SCOPE (a TenantScope, or
        None for tables with no farm linkage). Non-HTTP callers (no tenant context: flow runner,
        streamer, scripts) run unscoped by design. An authenticated caller with no farm can own no
        tenant rows, so they get an empty result rather than a leak.
        """
        scope = self.TENANT_SCOPE
        if scope is None:
            return query
        ctx = get_current_tenant()
        if ctx is None:
            return query
        farm = ctx.get("farm_name")
        if not farm:
            return query.filter(false())
        return scope.apply(query, self.MODEL, farm, session)

    def _bind_tenant(self, data: dict, session) -> dict:
        """
        Make a row being written belong to the caller's farm (TenantScope.bind). Non-HTTP callers
        and callers without a farm are not bound.
        """
        scope = self.TENANT_SCOPE
        ctx = get_current_tenant()
        if scope is None or ctx is None or not ctx.get("farm_name"):
            return data
        return scope.bind(data, self.MODEL, ctx["farm_name"], session)

    # ---- errors --------------------------------------------------------------------------

    def _translate(self, action: str, error: Exception, id=None):
        """Map a driver/ORM error to the domain exception the API layer knows how to answer."""
        if isinstance(error, (ConflictError, InvalidFilterError, NotFoundError, DBReposException)):
            return error
        suffix = f" with the id: {id}" if id is not None else ""
        if isinstance(error, IntegrityError):
            # The driver message names the violated constraint; keep it for the log, not the client.
            logger.warning("%s %s%s violates a constraint: %s", action, self.MODEL.__name__, suffix, error.orig)
            return ConflictError(f"{self.MODEL.__name__} conflicts with an existing record")
        return DBReposException(f"Error {action} {self.MODEL.__name__}{suffix}: {error}")

    # ---- CRUD ----------------------------------------------------------------------------

    def create(self, entity: ENTITY) -> ENTITY:
        """
        Create a new MODEL object.

        @param entity: data of the object to create.
        @type entity: ENTITY

        @return: ENTITY
        """
        session = self.Session()
        try:
            data = self._bind_tenant(entity.to_dict(), session)
            obj = self.MODEL(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            # obj is a model object
            # we want to return an Entity
            return self.ADAPTOR.model_to_entity(obj=obj)
        except Exception as e:
            session.rollback()
            raise self._translate("creating", e) from e
        finally:
            session.close()

    def get(self, id: int) -> ENTITY:
        """
            Get a Model by id
        logic:
            1- Connect to the db through Session
            2- Make action ( get ) on the db Session
            3- Convert Object to an Entity
        @param id:
        @return: ENTITY or None when missing / outside the caller's farm
        """
        session = self.Session()
        try:
            obj = self._apply_tenant(session.query(self.MODEL).filter(self.MODEL.id == id), session).one_or_none()
            return self.ADAPTOR.model_to_entity(obj=obj) if obj else None
        except Exception as e:
            raise self._translate("fetching", e, id) from e
        finally:
            session.close()

    def delete(self, id: int):
        """
         delete a Model by id
         logic:
            1- Connect to the db through Session
            2- Make action ( get ) on the db Session
            3- Delete the object from db
        @param id:
        @return: bool True if a row was deleted
        """
        session = self.Session()
        try:
            obj = self._apply_tenant(session.query(self.MODEL).filter(self.MODEL.id == id), session).one_or_none()
            if not obj:
                return False
            session.delete(obj)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise self._translate("deleting", e, id) from e
        finally:
            session.close()

    def update(self, id: int, data: dict) -> ENTITY:
        """
        Update a Model by id
         logic:
            1- Connect to the db through Session
            2- Make action ( get ) on the db Session
            3- Update the Object with the new data (READ_ONLY_FIELDS are ignored)
            4- Save it in the DB
            5- Return the Updated Object in form of an ENTITY
        @param id:
        @param data:
        @return: ENTITY or None when missing / outside the caller's farm
        """
        session = self.Session()
        try:
            obj = self._apply_tenant(session.query(self.MODEL).filter(self.MODEL.id == id), session).one_or_none()
            if not obj:
                # Not found, or outside the caller's farm -> 404 (do not reveal existence).
                return None
            data = self._bind_tenant(dict(data), session)
            for key, value in data.items():
                if key not in self.READ_ONLY_FIELDS:
                    setattr(obj, key, value)
            session.commit()
            session.refresh(obj)
            return self.ADAPTOR.model_to_entity(obj=obj)
        except Exception as e:
            session.rollback()
            raise self._translate("updating", e, id) from e
        finally:
            session.close()

    # ---- Filter DSL ------------------------------------------------------------------------
    # A filter is a list of {"attribute", "value", "condition"} dicts, interpreted below.
    # Endpoints produce it from the query string (BaseCrud.parse_filters); use cases build it inline.

    def _column(self, name: str):
        """
        A mapped column of MODEL; relationships, metadata and private attributes are not filterable.
        The entity's PRIVATE_FIELDS (a user's password hash) are stripped from every response, so
        they must not be queryable either: an equality filter on one is an oracle.
        """
        if name not in self.MODEL.__table__.columns or name in self.ENTITY.PRIVATE_FIELDS:
            raise InvalidFilterError(f"{self.MODEL.__name__} has no attribute '{name}'")
        return getattr(self.MODEL, name)

    def _build_query(self, session, filters, order_by, order_direction):
        query = self._apply_tenant(session.query(self.MODEL), session)
        conditions = []
        for item in filters:
            attribute = self._column(item["attribute"])
            value = item["value"]
            condition = item.get("condition", "eq")
            match condition:
                case "eq":
                    conditions.append(attribute == value)
                case "ne":
                    conditions.append(attribute != value)
                case "gt":
                    conditions.append(attribute > value)
                case "lt":
                    conditions.append(attribute < value)
                case "gte":
                    conditions.append(attribute >= value)
                case "lte":
                    conditions.append(attribute <= value)
                case "in":
                    conditions.append(attribute.in_(value if isinstance(value, list) else [value]))
                case "like":
                    conditions.append(attribute.like(value))
                case "ilike":
                    conditions.append(attribute.ilike(value))
                case "icontains":
                    conditions.append(attribute.ilike(f"%{value}%"))
                case _:
                    raise InvalidFilterError(f"Unsupported condition '{condition}'")
        if conditions:
            query = query.filter(and_(*conditions))
        direction = desc if order_direction == "desc" else asc
        return query.order_by(direction(self._column(order_by)))

    def filter(self, filters, order_by="created_date", order_direction="asc", limit=None, offset=None):
        """
        Apply filters to retrieve multiple models based on filter criteria.

        @param filters: A list of dictionaries specifying filtering conditions.
        Example:
            [
                {"attribute": "username", "value": "john", "condition": "eq"},
                {"attribute": "age", "value": 30, "condition": "gte"}
            ]
        @param order_by: The attribute by which to order the results. Default is "created_date".
        @param order_direction: The direction to order the results ('asc' or 'desc').
        @param limit: Optional maximum number of rows.
        @param offset: Optional number of rows to skip.
        @return: A list of ENTITY instances that match the filters.
        """
        session = self.Session()
        try:
            query = self._build_query(session, filters, order_by, order_direction)
            if offset:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            return [self.ADAPTOR.model_to_entity(obj) for obj in query.all()]
        except Exception as e:
            session.rollback()
            raise self._translate("filtering", e) from e
        finally:
            session.close()

    def first(self, filters, order_by="created_date", order_direction="desc"):
        """
        The first ENTITY for the filters and ordering, fetching a single row, or None.
        """
        result = self.filter(filters, order_by, order_direction, limit=1)
        return result[0] if result else None

    def count_by(self, attribute: str) -> dict:
        """
        Row counts grouped by one column, within the caller's farm: {value: count}. One query
        where a count per value would be one each.
        """
        session = self.Session()
        try:
            column = self._column(attribute)
            query = self._apply_tenant(session.query(column, func.count(self.MODEL.id)), session).group_by(column)
            return {value: n for value, n in query.all()}
        except Exception as e:
            session.rollback()
            raise self._translate("counting", e) from e
        finally:
            session.close()

    def count(self, filters):
        """
        Number of rows matching the filters, within the caller's farm.
        """
        session = self.Session()
        try:
            query = self._build_query(session, filters, "id", "asc").order_by(None)
            return query.with_entities(func.count(self.MODEL.id)).scalar() or 0
        except Exception as e:
            session.rollback()
            raise self._translate("counting", e) from e
        finally:
            session.close()

    def paginate(self, filters, order_by="created_date", order_direction="asc", limit=50, offset=0):
        """
        One page of ENTITY instances and the total count, both computed in the database.

        @return: tuple (items, total)
        """
        total = self.count(filters)
        items = self.filter(filters, order_by, order_direction, limit=limit, offset=offset) if total else []
        return items, total


class BaseBrokerRepo:
    """
    Gateway to the broker: publishes command events (water source / switcher on-off).
    A failed or unacknowledged delivery raises BrokerError so callers never record a
    state change that did not reach the field.
    """

    def __init__(self, producer=None, random_broker=None):
        """
        Initialize Broker Repo with producer and broker.
        @param producer: the broker producer
        @type producer

        """
        # Kafka broker configuration
        self.random_broker = random_broker
        # adding a broker producer
        self.producer = producer

    def push_event_to_broker(self, topic, key, event):
        """
        This method pushes an event to a broker and waits for the delivery report.
        @param topic:
        @param key:
        @param event:
        @raises BrokerError: when the broker rejected the message or did not acknowledge it in time
        """
        event_json = json.dumps(event)
        delivery_errors = []

        def on_delivery(error, _message):
            if error is not None:
                delivery_errors.append(error)

        logger.info("Pushing event %s.%s on broker %s", key, topic, self.random_broker)
        try:
            self._publish(topic, key, event_json, on_delivery, delivery_errors)
        except BrokerError:
            BROKER_COMMANDS.labels(topic, "failed").inc()
            raise
        BROKER_COMMANDS.labels(topic, "sent").inc()

    def _publish(self, topic, key, event_json, on_delivery, delivery_errors):
        try:
            self.producer.produce(topic, key=key, value=event_json.encode("utf-8"), on_delivery=on_delivery)
            remaining = self.producer.flush(BROKER_DELIVERY_TIMEOUT_SECONDS)
        except Exception as e:  # BufferError / KafkaException from librdkafka
            raise BrokerError(f"Could not publish {key} to {topic}: {e}") from e
        if delivery_errors:
            raise BrokerError(f"Broker rejected {key} on {topic}: {delivery_errors[0]}")
        if remaining:
            raise BrokerError(f"Broker did not acknowledge {key} on {topic} within {BROKER_DELIVERY_TIMEOUT_SECONDS}s")

    @staticmethod
    def generate_event(payload: dict):
        """
        this method helps to generate the event payload by adding the event type to it
        @param payload: the event payload : data
        @return: Payload of an event
        eg :
        { "sensor_serial_number": serial_number,
        "data": {
            "type": sensor_type,
            other data depends on the sensor type
            },
        }
        """
        return {
            "event_type": "status_data",
            **payload,  # Include additional payload data
        }

    def send_event(self, payload, topic, key):
        """
        This method sends an event on a topic with a key using the payload
        @param payload:
        @param topic:
        @param key:
        @raises BrokerError: see push_event_to_broker
        """
        event = self.generate_event(payload)
        logger.info("Sending event - Command : %s", event)
        self.push_event_to_broker(topic=topic, key=key, event=event)


class NoopBrokerRepo(BaseBrokerRepo):
    """
    Null Object broker for processes that must never actuate hardware (the API, the streamer,
    scripts). Commands are logged and dropped, so use cases need no `if broker_repo` branches.
    """

    def __init__(self):
        super().__init__(producer=None, random_broker="noop")

    def push_event_to_broker(self, topic, key, event):
        logger.debug("NoopBrokerRepo dropped %s.%s: %s", key, topic, event)
