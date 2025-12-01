.PHONY: help build up down logs scale clean test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs
	docker-compose logs -f

scale-backend: ## Scale backend to N replicas (usage: make scale-backend N=3)
	docker-compose up -d --scale backend=$(N)

scale-frontend: ## Scale frontend to N replicas (usage: make scale-frontend N=2)
	docker-compose up -d --scale frontend=$(N)

clean: ## Remove containers and volumes
	docker-compose down -v
	docker system prune -f

test: ## Run tests
	cd backend && python -m pytest tests/

health: ## Check health status
	curl http://localhost:8000/health

# Kubernetes targets
k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f deploy/k8s/configmap.yaml
	kubectl apply -f deploy/k8s/persistent-volumes.yaml
	kubectl apply -f deploy/k8s/backend/
	kubectl apply -f deploy/k8s/frontend/
	kubectl apply -f deploy/k8s/ingress.yaml
	kubectl apply -f deploy/k8s/hpa.yaml

k8s-delete: ## Delete Kubernetes resources
	kubectl delete -f deploy/k8s/

k8s-logs: ## View Kubernetes logs
	kubectl logs -f deployment/docvault-backend

k8s-scale: ## Scale Kubernetes deployment (usage: make k8s-scale DEPLOYMENT=docvault-backend REPLICAS=5)
	kubectl scale deployment $(DEPLOYMENT) --replicas=$(REPLICAS)

