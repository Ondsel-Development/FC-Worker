# FreeCAD Worker

## Building

```bash
docker build -t fc-worker .
```

## Running into development mode 

```bash
docker run -p 9000:8080 -v <path_of_fc_worker>:/fc_worker --name fc_worker fc-worker:latest
```

## Testing

```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"command": "health_check"}'
```