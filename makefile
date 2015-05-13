
all: build

build: src models language

.PHONY: src
src:
	@$(MAKE) -C src

.PHONY: models
models:
	@$(MAKE) -C models

.PHONY: language
language:
	@$(MAKE) -C language

clean:
	@$(MAKE) clean -C src
	@$(MAKE) clean -C models
	@$(MAKE) clean -C language

pack-zip: build
	./util/pack_zip.sh

