import json
import logging
import time
from datetime import datetime
from functools import lru_cache

from sqlalchemy import asc, desc
from sqlalchemy import create_engine, and_, false
from sqlalchemy.orm import sessionmaker

from infrastructure.exceptions import DBReposException
from common.tenant_context import get_current_tenant

logger = logging.getLogger(__name__)


class BaseDBRepo:
    """
    BaseDBRepo is an Abstract Class
    """

    MODEL = None
    ENTITY = None
    ADAPTOR = None
    READ_ONLY_FIELDS = ["id", "created_date"]
    # Per-farm tenancy scope, overridden per repository. One of:
    #   ("column", "<farm column>") direct farm column on the model
    #   ("self", "<farm column>")   the farm row itself
    #   ("via_zone",)               model.zone_name -> zone.farm_name
    #   None                        not tenant-scoped (no farm linkage)
    TENANT_SCOPE = None

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

    @classmethod
    @lru_cache(maxsize=None)
    def get_engine(cls, uri: str, echo: bool):
        """
        Get the SQLAlchemy engine.

        @param uri: Database URI.
        @type uri: str
        @param echo: Debug mode.
        @type echo: bool

        @return: SQLAlchemy engine.
        @rtype: sqlalchemy.engine.base.Engine
        """
        try:
            return create_engine(uri, echo=echo)
        except Exception as e:
            raise Exception(f"Error creating engine {uri}: {e}")

    def _apply_tenant(self, query, session):
        """Restrict a query to the caller's farm, per this repo's TENANT_SCOPE.

        Non-HTTP callers (no tenant context) run unscoped by design. An
        authenticated caller with no farm can own no tenant rows, so we return
        an empty result rather than leaking. Models with TENANT_SCOPE=None are
        not scoped (no farm linkage in the schema).
        """
        scope = self.TENANT_SCOPE
        if not scope:
            return query
        ctx = get_current_tenant()
        if ctx is None:
            return query  # internal/non-HTTP caller (flow runner, streamer, scripts)
        farm = ctx.get("farm_name")
        if not farm:
            return query.filter(false())
        kind = scope[0]
        if kind in ("column", "self"):
            return query.filter(getattr(self.MODEL, scope[1]) == farm)
        if kind == "via_zone":
            from infrastructure.database.tables.zone import Zone
            owned_zones = session.query(Zone.zone_name).filter(Zone.farm_name == farm)
            return query.filter(self.MODEL.zone_name.in_(owned_zones))
        return query

    def create(self, entity: ENTITY) -> ENTITY:
        """
        Create a new MODEL object.

        @param entity: data of the object to create.
        @type entity: ENTITY

        @return: ENTITY
        """
        session = self.Session()
        data = entity.to_dict()
        try:
            obj = self.MODEL(**data)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            # obj is a model object
            # we want to return an Entity
            return self.ADAPTOR.model_to_entity(obj=obj)
        except Exception as e:
            session.rollback()
            raise DBReposException(f"Error creating {self.MODEL.__name__}: {e}")
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
        @return: ENTITY
        """
        session = self.Session()

        result = None

        try:
            obj = self._apply_tenant(session.query(self.MODEL).filter(self.MODEL.id == id), session).one_or_none()
            if obj:
                result = self.ADAPTOR.model_to_entity(obj=obj)
            return result
        except Exception as e:
            raise DBReposException(f"Error Fetching the {self.MODEL.__name__} with the id: {id}: {e}")
        finally:
            session.close()

    def delete(self, id: int):
        """
         delete a Model by id
         logic:
            1- Connect to the db through Session
            2- Make action ( get ) on the db Session
            3- Convert Object to an Entity and save it in result
            4- Delete the object from db
            5- Return the Deleted Object in form of an ENTITY

        @param id:
        @return: ENTITY
        """
        session = self.Session()
        is_deleted = False
        try:
            obj = self._apply_tenant(session.query(self.MODEL).filter(self.MODEL.id == id), session).one_or_none()
            if obj:
                session.delete(obj)
                session.commit()
                is_deleted = True

        except Exception as e:
            raise Exception(f"Error Deleting the {self.MODEL.__name__} with the id: {id}: {e}")
        finally:
            session.close()
        return is_deleted

    def update(self, id: int, data: dict) -> ENTITY:
        """
        Update a Model by id
         logic:
            1- Connect to the db through Session
            2- Make action ( get ) on the db Session
            3- Convert the entity to an object
            4- Update the Object with the new object (from the entity)
            5- Save it in the DB
            5- Return the Updated Object in form of an ENTITY
        @param id:
        @param data:
        @return:ENTITY
        """

        session = self.Session()

        try:
            obj = self._apply_tenant(session.query(self.MODEL).filter(self.MODEL.id == id), session).one_or_none()
            if not obj:
                # Not found, or outside the caller's farm -> 404 (do not reveal existence).
                return None

            for key, value in data.items():
                if key not in self.READ_ONLY_FIELDS:
                    setattr(obj, key, value)
            session.commit()  # Commit the changes to the database
            session.refresh(obj)  # Refresh the instance to get the updated data
            result = self.ADAPTOR.model_to_entity(obj=obj)  # Convert the updated model to an entity

            return result
        except Exception as e:
            raise Exception(f"Error Updating the {self.MODEL.__name__} with the id: {id}: {e}")
        finally:
            session.close()  # Ensure the session is closed properly

    def filter(self, filters, order_by="created_date", order_direction="asc"):
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
        @return: A list of ENTITY instances that match the filters.
        """
        session = self.Session()
        query = self._apply_tenant(session.query(self.MODEL), session)
        conditions = []

        for filter in filters:
            attribute = getattr(self.MODEL, filter['attribute'])
            value = filter['value']
            condition = filter.get('condition', 'eq')
            match condition:
                case 'eq':
                    conditions.append(attribute == value)
                case 'ne':
                    conditions.append(attribute != value)
                case 'gt':
                    conditions.append(attribute > value)
                case 'lt':
                    conditions.append(attribute < value)
                case 'gte':
                    conditions.append(attribute >= value)
                case 'lte':
                    conditions.append(attribute <= value)
                case 'in':
                    conditions.append(attribute.in_(value if isinstance(value, list) else [value]))
                case 'like':
                    conditions.append(attribute.like(value))
                case 'ilike':
                    conditions.append(attribute.ilike(value))
                case 'icontains':
                    conditions.append(attribute.ilike(f"%{value}%"))
                case _:
                    raise ValueError(f"Unsupported condition '{condition}'")

        query = query.filter(and_(*conditions))
        if order_direction == "desc":
            query = query.order_by(desc(getattr(self.MODEL, order_by)))
        else:
            query = query.order_by(asc(getattr(self.MODEL, order_by)))

        try:
            result = query.all()
            return [self.ADAPTOR.model_to_entity(obj) for obj in result]
        except Exception as e:
            session.rollback()
            raise DBReposException(f"Error filtering {self.MODEL.__name__}: {e}")
        finally:
            session.close()


class BaseBrokerRepo:

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
        This method pushes an event to a broker
        @param topic:
        @param key:
        @param event:
        @return:
        """
        # Encode the event as a JSON string
        event_json = json.dumps(event)

        # Produce the event to the specified topic
        logger.info(f"Pushing event {key}.{topic} on broker {self.random_broker}")

        self.producer.produce(topic, key=key, value=event_json.encode("utf-8"))
        # Flush the producer to ensure the message is sent
        self.producer.flush()

    @staticmethod
    def generate_event(payload: dict):
        """
        this method helps to generate the event payload by adding to it
        timestamp using the class method get_formatted_now_date
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
        event_data = {
            "event_type": "status_data",
            **payload  # Include additional payload data

        }
        return event_data

    def send_event(self, payload, topic, key):
        """
        This method sends an event on a topic with a key using the payload
        @param payload:
        @param topic:
        @param key:
        @return:
        """
        event = self.generate_event(payload)
        # Send event to Kafka broker
        logger.info(f"Sending event - Command : {event}")
        time.sleep(0.1)  # Simulate some delay between events
        self.push_event_to_broker(topic=topic, key=key, event=event)
