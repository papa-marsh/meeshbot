.PHONY: shell
shell:
	uv run --env-file .env ipython -i meeshbot/shell.py

.PHONY: deploy
deploy:
	docker compose down && \
	docker compose up -d --build && \
	sleep 1 && \
	make logs


.PHONY: pull-deploy
pull-deploy:
	git checkout main && \
	git pull && \
	make deploy

.PHONY: pull-deploy-f
pull-deploy-f:
	git checkout main && \
	git fetch origin && \
	git reset --hard origin/main && \
	git pull && \
	make deploy

.PHONY: logs
logs:
	docker compose logs meeshbot
