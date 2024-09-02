# 测试 ./target 与 target 之间能否互相匹配

single_targets := ./xxx/1 ././xxx/2 ./3 ././4 \
		   xxx/5 6 7

PHONY += $(single_targets)

$(single_targets):
	@echo build $@

.PHONY: $(PHONY)

pattern_targets := 8/a.a 9/a.a 10/a.a
PHONY += $(pattern_targets)

# 模式匹配 中也可以加上 ./
# 8/a.a 可以成功的匹配上 ./%/a.a 然后 % 被替换为 8
# 然后 ./8 可以继续去匹配 8
$(pattern_targets): ./%/a.a: ./%

pattern_subdirs := $(patsubst %/a.a, %, $(pattern_targets))
PHONY += $(pattern_subdirs)

# 定义 target 8 9 10
$(pattern_subdirs): 
	@echo build subdir $@

test:
	@# 没有./开头的目标 匹配 ./ 开头的目标
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) xxx/1
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) xxx/2
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) 3
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) 4

	@# ./ 开头的目标匹配 没有 ./ 开头的目标
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ././xxx/5
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ./6
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ././7

	@# ./8/a.a -> 8/a.a -> ./8/a.a -> ./8 -> 8
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ./8/a.a
