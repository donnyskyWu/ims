.PHONY: api worker test ci

api:
	go run ./cmd/api

worker:
	go run ./cmd/worker

test:
	go test ./...

ci:
	go test ./internal/architecture
