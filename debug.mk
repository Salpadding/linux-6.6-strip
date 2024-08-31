define fn
$(1): def
	@echo $$<
endef

$(eval $(call fn,abc))


def:

.PHONY: def
