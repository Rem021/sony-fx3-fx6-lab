LIBUSB_SRC_DIR = /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage142-Mac-USB-transport-candidate/work/libusb-1.0.30/libusb
EXCLUDED_FILES = libusbi.h version.h version_nano.h
LIBUSB_SRC = $(wildcard $(LIBUSB_SRC_DIR)/*.c) $(wildcard $(LIBUSB_SRC_DIR)/*.h)
LIBUSB_DOC_SRC = $(filter-out $(addprefix $(LIBUSB_SRC_DIR)/,$(EXCLUDED_FILES)),$(LIBUSB_SRC))

docs: api-1.0

api-1.0: doxygen.cfg /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage142-Mac-USB-transport-candidate/work/libusb-1.0.30/doc/libusb.png $(LIBUSB_DOC_SRC)
	doxygen $<

sfurl = web.sourceforge.net:/home/project-web/libusb/htdocs
docs-upload: api-1.0
	if [ -z "$$SF_USER" ]; then \
		rsync -rv --delete $< $(sfurl); \
	else \
		rsync -rv --delete $< $$SF_USER@$(sfurl); \
	fi

clean:
	rm -rf api-1.0

.PHONY: clean docs docs-upload
