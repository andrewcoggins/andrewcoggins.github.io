shell:
	docker-compose run --rm ruby sh

compile:
	docker run --rm -v "$PWD":/usr/src/app -w /usr/src/app ruby:2.5 bundle install

build-environment:
	docker-compose build