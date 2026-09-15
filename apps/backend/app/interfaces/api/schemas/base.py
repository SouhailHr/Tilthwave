"""
Shared pieces of the request schemas.

Update (PATCH) schemas forbid unknown fields but *accept and ignore* the resource identifiers:
the web edit forms send the whole record back, and rejecting `zone_name` on a zone edit would
break every dialog, while applying it would let a caller rename or move a resource through a
partial update. Such fields are declared with `exclude=True` so `model_dump()` never emits them.
"""

IDENTIFIER_DOC = "Identifier echoed back by edit forms; accepted and ignored, it cannot be changed here."
