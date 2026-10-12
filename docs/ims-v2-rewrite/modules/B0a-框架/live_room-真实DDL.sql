-- Football 直播库真实 live_room 表结构（zhang wu 2026-10-12 提供）
-- 源库：shenyu-live（主机由运维 / 上线前联调提供只读连接；开发期不直连）
-- 用途：IMS 开发 / 测试 / E2E 替身表须与本 DDL 同名、同列、同类型、同含义一字不差建表
-- 注意：旧 opsbiz.live_room 桩表不得作为替身模板
-- 敏感列：bind_mobile_password、login_pwd —— 替身表结构保留，seed 用假数据；
--         IMS 只读连接不得用于写这些字段；展示脱敏

CREATE TABLE `live_room`  (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `author_id` bigint(20) NULL DEFAULT NULL COMMENT '作者ID',
  `nickname` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '作者昵称',
  `avatar_url` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '作者头像',
  `live_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播间ID',
  `live_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播名称',
  `cover` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '封面图',
  `status` tinyint(4) NULL DEFAULT NULL COMMENT '状态 1=未开始 2=直播中 3=已结束 4=过期 5=暂停',
  `live_mode` tinyint(4) NULL DEFAULT NULL COMMENT '模式 1=直播 2=录播',
  `screen_type` tinyint(4) NULL DEFAULT NULL COMMENT '观看模式 1=横屏 2=竖屏',
  `template_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '观看页模板ID',
  `watch_type` tinyint(4) NULL DEFAULT NULL COMMENT '直播间类型 1=公开 2=付费 3=加密',
  `enable_playback` tinyint(4) NULL DEFAULT NULL COMMENT '回放 0=关闭 1=开启回放',
  `enable_low_latency` tinyint(4) NULL DEFAULT NULL COMMENT '低延时 0=关闭 1=开启低延迟',
  `enable_heat` tinyint(4) NULL DEFAULT NULL COMMENT '热力值 0=关闭 1=开启热力值',
  `enable_completion` tinyint(4) NULL DEFAULT NULL COMMENT '完播统计 0=关闭 1=开启完播统计',
  `start_time` datetime NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime NULL DEFAULT NULL COMMENT '结束时间',
  `view_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '观看地址',
  `playback_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '回放地址',
  `server_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '推流地址',
  `stream_key` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '推流码',
  `flv_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'flvUrl播放地址',
  `hls_live_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'hls播流地址',
  `tenant_id` bigint(20) NULL DEFAULT NULL COMMENT '租户',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `creator` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `updater` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `deleted` tinyint(4) NULL DEFAULT 0 COMMENT '是否删除',
  `bind_product_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '绑定商品ID',
  `bind_mobile` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '绑定直播账号',
  `bind_mobile_password` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '绑定直播账号密码',
  `reserve_count` int(11) NULL DEFAULT 0,
  `like_count` int(11) NULL DEFAULT 0,
  `virtual_like_count` int(11) NULL DEFAULT 0 COMMENT '虚拟点赞数',
  `viewer_count` int(11) NULL DEFAULT 0 COMMENT '观看人数',
  `login_pwd` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_author_id`(`author_id`) USING BTREE,
  INDEX `idx_tenant_id`(`tenant_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '直播间表';
