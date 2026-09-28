-- Legacy Prototype akoni_db Backup generated at 2026-09-28T16:40:35.882782
CREATE DATABASE IF NOT EXISTS `akoni_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `akoni_db`;
SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `customers`;
CREATE TABLE `customers` (
  `customer_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `customer_first_name` varchar(100) NOT NULL,
  `customer_last_name` varchar(100) NOT NULL,
  `contact_number` varchar(30) NOT NULL,
  `address` varchar(255) NOT NULL,
  `email_address` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `expenses`;
CREATE TABLE `expenses` (
  `expense_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `expense_date` date NOT NULL,
  `expense_category` enum('Labor','Materials','Miscellaneous','Utilities','Other') NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`expense_id`),
  KEY `idx_expense_date` (`expense_date`),
  KEY `idx_expense_category` (`expense_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `inventory_movements`;
CREATE TABLE `inventory_movements` (
  `movement_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `material_id` int(10) unsigned NOT NULL,
  `movement_type` enum('Stock In','Stock Out') NOT NULL,
  `quantity` decimal(12,2) NOT NULL,
  `movement_date` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`movement_id`),
  KEY `idx_inventory_material` (`material_id`),
  KEY `idx_inventory_date` (`movement_date`),
  CONSTRAINT `fk_inventory_movements_material` FOREIGN KEY (`material_id`) REFERENCES `materials` (`material_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `materials`;
CREATE TABLE `materials` (
  `material_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `material_name` varchar(150) NOT NULL,
  `low_stock_level` decimal(12,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`material_id`),
  KEY `idx_material_name` (`material_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `payments`;
CREATE TABLE `payments` (
  `payment_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `transaction_id` int(10) unsigned NOT NULL,
  `payment_type` enum('Layout Design','Design Assurance','Product Order','Rush Payment') NOT NULL,
  `payment_method` enum('Cash','GCash','Bank Transfer') NOT NULL,
  `amount_paid` decimal(12,2) NOT NULL DEFAULT 0.00,
  `payment_date` date NOT NULL,
  `payment_status` enum('Pending','Verified') NOT NULL DEFAULT 'Pending',
  PRIMARY KEY (`payment_id`),
  KEY `idx_payments_transaction` (`transaction_id`),
  KEY `idx_payments_date` (`payment_date`),
  KEY `idx_payments_status` (`payment_status`),
  CONSTRAINT `fk_payments_transaction` FOREIGN KEY (`transaction_id`) REFERENCES `sales_transactions` (`transaction_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `sales_transactions`;
CREATE TABLE `sales_transactions` (
  `transaction_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `customer_id` int(10) unsigned NOT NULL,
  `transaction_type` enum('Layout Design Only','Customized Product Order') NOT NULL,
  `transaction_date` date NOT NULL,
  `product_specification` text DEFAULT NULL,
  `quantity` int(10) unsigned NOT NULL DEFAULT 0,
  `amount_due` decimal(12,2) NOT NULL DEFAULT 0.00,
  `expected_delivery_date` date DEFAULT NULL,
  `rush_charge` decimal(12,2) NOT NULL DEFAULT 0.00,
  `design_assurance_deduction` decimal(12,2) NOT NULL DEFAULT 0.00,
  `release_method` enum('Customer Pickup','Nearby Delivery','Courier Shipment') DEFAULT NULL,
  `selected_courier` varchar(100) DEFAULT NULL,
  `actual_delivery_date` date DEFAULT NULL,
  `transaction_status` enum('Pending','Ongoing','Completed') NOT NULL DEFAULT 'Pending',
  PRIMARY KEY (`transaction_id`),
  KEY `idx_sales_customer` (`customer_id`),
  KEY `idx_sales_transaction_date` (`transaction_date`),
  KEY `idx_sales_status` (`transaction_status`),
  CONSTRAINT `fk_sales_transactions_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`customer_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('Admin','Staff') NOT NULL,
  `status` enum('Active','Inactive') NOT NULL DEFAULT 'Active',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `users` (`user_id`, `first_name`, `last_name`, `username`, `password_hash`, `role`, `status`) VALUES (1, 'System', 'Administrator', 'admin', 'admin123', 'Admin', 'Active');
INSERT INTO `users` (`user_id`, `first_name`, `last_name`, `username`, `password_hash`, `role`, `status`) VALUES (2, 'System', 'Staff', 'staff', 'staff123', 'Staff', 'Active');

SET FOREIGN_KEY_CHECKS=1;
