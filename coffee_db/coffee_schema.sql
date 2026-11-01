-- =====================================================================
-- COFFEE 咖啡连锁示例库 —— MySQL 8.0 方言 DDL
-- 个人求职项目用(表结构自己设计,数据 build_coffee.py 生成)
-- 用途:schema 语义化来源(表/列 COMMENT + 外键);执行层用 SQLite(build 时 transpile)
-- =====================================================================

-- 门店
CREATE TABLE store (
    id        INT         PRIMARY KEY AUTO_INCREMENT COMMENT '门店ID',
    name      VARCHAR(50) NOT NULL COMMENT '门店名称',
    city      VARCHAR(20) NOT NULL COMMENT '所在城市',
    district  VARCHAR(30) NOT NULL COMMENT '所在区域',
    open_date DATE        NOT NULL COMMENT '开业日期'
) COMMENT='门店表';

-- 品类
CREATE TABLE category (
    id   INT         PRIMARY KEY AUTO_INCREMENT COMMENT '品类ID',
    name VARCHAR(50) NOT NULL COMMENT '品类名称'
) COMMENT='品类表';

-- 商品
CREATE TABLE product (
    id          INT           PRIMARY KEY AUTO_INCREMENT COMMENT '商品ID',
    category_id INT           NOT NULL COMMENT '所属品类ID',
    name        VARCHAR(100)  NOT NULL COMMENT '商品名称',
    price       DECIMAL(10,2) NOT NULL COMMENT '售价(元)',
    is_active   TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否在售',
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES category(id)
) COMMENT='商品表';

-- 会员
CREATE TABLE customer (
    id            INT         PRIMARY KEY AUTO_INCREMENT COMMENT '会员ID',
    name          VARCHAR(50) NOT NULL COMMENT '会员姓名',
    phone         VARCHAR(20) NOT NULL COMMENT '手机号',
    level         VARCHAR(10) NOT NULL DEFAULT '普通' COMMENT '会员等级：普通, 银卡, 金卡, 黑金',
    registered_at DATETIME    NOT NULL COMMENT '注册时间'
) COMMENT='会员表';

-- 订单
CREATE TABLE orders (
    id             INT           PRIMARY KEY AUTO_INCREMENT COMMENT '订单ID',
    store_id       INT           NOT NULL COMMENT '门店ID',
    customer_id    INT           NOT NULL COMMENT '会员ID',
    order_date     DATETIME      NOT NULL COMMENT '下单时间',
    status         VARCHAR(10)   NOT NULL DEFAULT '已完成' COMMENT '订单状态：已完成, 已取消, 退款中',
    total_amount   DECIMAL(10,2) NOT NULL COMMENT '订单总额(元)',
    payment_method VARCHAR(10)   NOT NULL DEFAULT '微信' COMMENT '支付方式：微信, 支付宝, 银行卡, 现金',
    CONSTRAINT fk_order_store    FOREIGN KEY (store_id)    REFERENCES store(id),
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customer(id)
) COMMENT='订单表';

-- 订单明细
CREATE TABLE order_item (
    id         INT           PRIMARY KEY AUTO_INCREMENT COMMENT '明细ID',
    order_id   INT           NOT NULL COMMENT '订单ID',
    product_id INT           NOT NULL COMMENT '商品ID',
    quantity   INT           NOT NULL COMMENT '数量',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '成交单价(元)',
    amount     DECIMAL(10,2) NOT NULL COMMENT '小计金额(元)',
    CONSTRAINT fk_item_order   FOREIGN KEY (order_id)   REFERENCES orders(id),
    CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES product(id)
) COMMENT='订单明细表';

-- 促销
CREATE TABLE promotion (
    id         INT          PRIMARY KEY AUTO_INCREMENT COMMENT '促销ID',
    name       VARCHAR(100) NOT NULL COMMENT '促销名称',
    discount   DECIMAL(4,2) NOT NULL DEFAULT 1.00 COMMENT '折扣系数(0.50=五折)',
    start_date DATE         NOT NULL COMMENT '开始日期',
    end_date   DATE         NOT NULL COMMENT '结束日期'
) COMMENT='促销表';
