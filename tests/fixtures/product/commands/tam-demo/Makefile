PREFIX ?= /usr/local

.PHONY: check install

check:
	test "$$(./tam-demo)" = demo

install:
	install -Dm755 tam-demo $(DESTDIR)$(PREFIX)/bin/tam-demo
