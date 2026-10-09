-- 竞品关键词「是否采集」。已有 oa_collect_keyword 缺列时执行；create_all 新库无需再跑。

ALTER TABLE oa_collect_keyword
  ADD COLUMN collect_enabled TINYINT NOT NULL DEFAULT 1 COMMENT '是否进入外部统一任务成员';
