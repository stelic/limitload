mo_files := $(shell find -name '*.po' | sort | sed 's/\.po/.mo/')

# For every sr.mo set to automatically derive sr@latin.mo.
mo_files := $(shell echo " $(mo_files)" \
                    | sed 's: \([^ ]*\)sr\.mo: \1sr.mo \1sr@latin.mo:g')

all: $(mo_files)

%.mo: %.po
	../util/po-compile.sh $<

%/sr@latin.po: %/sr.po
	msgfilter -i $< -o $@ recode-sr-latin
# Using msgfilter instead of recode-sr-latin command
# to avoid encoding detection problems.

clean:
	rm -rf $(mo_files) mo

