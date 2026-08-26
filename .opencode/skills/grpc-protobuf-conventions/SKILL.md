---
name: grpc-protobuf-conventions
description: gRPC service design, protobuf conventions, and API versioning.
origin: Custom
---
gRPC conventions: Use proto3. Prefix message types with service name. Use enums over strings for status/type fields. Version packages (v1/, v2/). Prefer unary for request-response, streams for bulk data. Activate when writing or reviewing gRPC services.
