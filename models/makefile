
eggz_files = $(shell find -name '*.egg' | sort | sed 's/\.egg/.egg.pz/')

all: $(eggz_files)

%.egg.pz: %.egg
	pzip $< 2>/dev/null

clean:
