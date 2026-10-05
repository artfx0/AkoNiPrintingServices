"""Complete System Seeder for AkoNi Printing Services (MySQL + PyQt6).

Populates all application tables with realistic, interconnected dummy data
spanning the last 6 months for end-to-end testing, reports, and UI verification.

Tables Seeded (Respecting Foreign Keys):
  1. Users (Ensures admin / admin123 exists with bcrypt; preserves Staff users)
  2. Customers (10 realistic Filipino profiles with 11-digit PH mobile numbers)
  3. Materials (10 materials, exactly 2 falling below low_stock_threshold)
  4. CustomerOrders (15 orders across 6 months; 3 LayoutOnly, 12 ProductOrders;
     rush charges, design fee deductions, and mixed statuses)
  5. OrderItems (1-3 items per ProductOrder with custom finishes and sizes)
  6. Payments (Linked to orders + 2 standalone Layout-Only payments; all Completed)
  7. Expenses (20 expenses across 6 months in Labor, Materials, Utility, Misc, Other)
  8. StockMovements (IN restock linked to expenses, OUT linked to order items,
     and 1 ADJUSTMENT movement)

Usage:
  python seeder.py           # Prompts before cleaning if data exists
  python seeder.py --clean   # Cleans transactional tables and reseeds automatically
  python seeder.py --force   # Non-interactive clean and reseed
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Ensure application root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bcrypt
from database.database import get_connection, init_database


# ---------------------------------------------------------------------------
# Data Definitions
# ---------------------------------------------------------------------------

CUSTOMERS_DATA = [
    {
        "first_name": "Juan",
        "last_name": "Dela Cruz",
        "contact_number": "09171234567",
        "email_address": "juan.delacruz@gmail.com",
        "address": "124 Rizal St., Brgy. Poblacion, Makati City",
        "created_at": datetime(2026, 4, 2, 9, 30),
    },
    {
        "first_name": "Maria",
        "last_name": "Santos",
        "contact_number": "09182345678",
        "email_address": "maria.santos@yahoo.com",
        "address": "77 Mabini Ave., Malate, Manila",
        "created_at": datetime(2026, 4, 15, 11, 20),
    },
    {
        "first_name": "Mark Joshua",
        "last_name": "Bautista",
        "contact_number": "09203456789",
        "email_address": "mj.bautista@outlook.com",
        "address": "Lot 12 Block 5, Commonwealth, Quezon City",
        "created_at": datetime(2026, 5, 4, 14, 15),
    },
    {
        "first_name": "Angelica",
        "last_name": "Reyes",
        "contact_number": "09274567890",
        "email_address": "angelica.reyes@gmail.com",
        "address": "45 Bonifacio St., San Antonio, Pasig City",
        "created_at": datetime(2026, 5, 12, 10, 45),
    },
    {
        "first_name": "Bea Alonzo",
        "last_name": "Tan",
        "contact_number": "09325678901",
        "email_address": "bea.tan@creativebiz.ph",
        "address": "88 Ayala Ave., San Lorenzo, Makati City",
        "created_at": datetime(2026, 6, 1, 16, 0),
    },
    {
        "first_name": "Christian Dale",
        "last_name": "Rivera",
        "contact_number": "09456789012",
        "email_address": "cd.rivera@techsolutions.com",
        "address": "15 J.P. Laurel Ave., Bajada, Davao City",
        "created_at": datetime(2026, 6, 18, 13, 30),
    },
    {
        "first_name": "Katrina Mae",
        "last_name": "Garcia",
        "contact_number": "09567890123",
        "email_address": "katrina.garcia@gmail.com",
        "address": "202 Osmeña Blvd., Capitol Site, Cebu City",
        "created_at": datetime(2026, 7, 5, 9, 10),
    },
    {
        "first_name": "John Paul",
        "last_name": "Lim",
        "contact_number": "09668901234",
        "email_address": "jp.lim@creativehub.ph",
        "address": "54 Shaw Blvd., Mandaluyong City",
        "created_at": datetime(2026, 7, 20, 15, 40),
    },
    {
        "first_name": "Sarah Joy",
        "last_name": "Hernandez",
        "contact_number": "09779012345",
        "email_address": "sarah.hernandez@deped.gov.ph",
        "address": "16 Magsaysay St., Session Rd., Baguio City",
        "created_at": datetime(2026, 8, 3, 11, 50),
    },
    {
        "first_name": "Gabriel",
        "last_name": "Mendoza",
        "contact_number": "09980123456",
        "email_address": "gabriel.mendoza@foodcart.ph",
        "address": "93 MacArthur Highway, San Fernando, Pampanga",
        "created_at": datetime(2026, 8, 22, 17, 15),
    },
]

# 10 Materials: Notice Kraft Paper (5 vs 20) and Ink Cyan (3 vs 10) trigger LOW STOCK alerts!
MATERIALS_DATA = [
    {
        "material_name": "Kraft Paper (70gsm)",
        "unit_of_measure": "reams",
        "current_stock_qty": 5,          # Low stock! (5 <= 20)
        "low_stock_threshold": 20,
        "cost_per_unit": Decimal("350.00"),
    },
    {
        "material_name": "Glossy Photo Paper (A4 230gsm)",
        "unit_of_measure": "packs",
        "current_stock_qty": 140,
        "low_stock_threshold": 25,
        "cost_per_unit": Decimal("185.00"),
    },
    {
        "material_name": "Matte Sticker Paper (A4)",
        "unit_of_measure": "packs",
        "current_stock_qty": 85,
        "low_stock_threshold": 20,
        "cost_per_unit": Decimal("145.00"),
    },
    {
        "material_name": "Ink Cartridge - Black (Dye)",
        "unit_of_measure": "bottles",
        "current_stock_qty": 18,
        "low_stock_threshold": 10,
        "cost_per_unit": Decimal("450.00"),
    },
    {
        "material_name": "Ink Cartridge - Cyan (Dye)",
        "unit_of_measure": "bottles",
        "current_stock_qty": 3,           # Low stock! (3 <= 10)
        "low_stock_threshold": 10,
        "cost_per_unit": Decimal("450.00"),
    },
    {
        "material_name": "Ink Cartridge - Magenta (Dye)",
        "unit_of_measure": "bottles",
        "current_stock_qty": 14,
        "low_stock_threshold": 10,
        "cost_per_unit": Decimal("450.00"),
    },
    {
        "material_name": "Ink Cartridge - Yellow (Dye)",
        "unit_of_measure": "bottles",
        "current_stock_qty": 12,
        "low_stock_threshold": 10,
        "cost_per_unit": Decimal("450.00"),
    },
    {
        "material_name": "Packaging Heavy-Duty Tape",
        "unit_of_measure": "rolls",
        "current_stock_qty": 42,
        "low_stock_threshold": 15,
        "cost_per_unit": Decimal("65.00"),
    },
    {
        "material_name": "Industrial Binding Glue",
        "unit_of_measure": "bottles",
        "current_stock_qty": 24,
        "low_stock_threshold": 8,
        "cost_per_unit": Decimal("120.00"),
    },
    {
        "material_name": "Corrugated Shipping Boxes (M)",
        "unit_of_measure": "pcs",
        "current_stock_qty": 110,
        "low_stock_threshold": 30,
        "cost_per_unit": Decimal("28.00"),
    },
]

# 15 Orders distributed across 6 months:
# 3 LayoutOnly, 12 ProductOrders
# Mix of statuses: Pending (2), Processing (3), Paid (3), Ready (2), Delivered (4), Cancelled (1)
# 2 orders with is_design_fee_deducted = True (quantity >= 100)
# 2 orders with rush_charge > 0
ORDERS_DATA = [
    # Month 1: April 2026
    {
        "order_idx": 1,
        "customer_idx": 0,  # Juan Dela Cruz
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 4, 10, 10, 15),
        "expected_delivery_date": datetime(2026, 4, 15, 17, 0),
        "actual_delivery_date": datetime(2026, 4, 14, 15, 30),
        "status": "Delivered",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "124 Rizal St., Brgy. Poblacion, Makati City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Corrugated Box",
                "finish_type": "Matte",
                "size": "Medium (6x9)",
                "quantity": 100,
                "unit_price": Decimal("15.00"),
                "discount": Decimal("0.00"),
                "design_file_path": "designs/order_001_box.pdf",
            },
        ],
    },
    {
        "order_idx": 2,
        "customer_idx": 1,  # Maria Santos
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 4, 22, 14, 30),
        "expected_delivery_date": datetime(2026, 4, 28, 17, 0),
        "actual_delivery_date": datetime(2026, 4, 27, 16, 0),
        "status": "Delivered",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "77 Mabini Ave., Malate, Manila",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Kraft Pouch",
                "finish_type": "Plain",
                "size": "4x6 inches",
                "quantity": 200,
                "unit_price": Decimal("6.50"),
                "discount": Decimal("50.00"),
                "design_file_path": "designs/order_002_pouch.pdf",
            },
            {
                "packaging_type": "Glossy Sticker",
                "finish_type": "Glossy",
                "size": "2x2 inches",
                "quantity": 200,
                "unit_price": Decimal("2.50"),
                "discount": Decimal("0.00"),
                "design_file_path": "designs/order_002_stickers.pdf",
            },
        ],
    },

    # Month 2: May 2026
    {
        "order_idx": 3,
        "customer_idx": 2,  # Mark Joshua Bautista
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 5, 8, 11, 0),
        "expected_delivery_date": datetime(2026, 5, 14, 17, 0),
        "actual_delivery_date": datetime(2026, 5, 13, 14, 20),
        "status": "Delivered",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "Lot 12 Block 5, Commonwealth, Quezon City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Hardcover Box",
                "finish_type": "Laminated",
                "size": "A4",
                "quantity": 50,
                "unit_price": Decimal("45.00"),
                "discount": Decimal("100.00"),
                "design_file_path": "designs/order_003_hardcover.pdf",
            },
        ],
    },
    {
        "order_idx": 4,
        "customer_idx": 3,  # Angelica Reyes
        "order_type": "LayoutOnly",
        "order_date": datetime(2026, 5, 18, 16, 20),
        "expected_delivery_date": datetime(2026, 5, 20, 17, 0),
        "actual_delivery_date": None,
        "status": "Paid",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "Digital File Email Delivery",
        "is_design_fee_deducted": False,
        "items": [],
        "override_total": Decimal("500.00"),
    },

    # Month 3: June 2026
    {
        "order_idx": 5,
        "customer_idx": 4,  # Bea Alonzo Tan
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 6, 4, 9, 45),
        "expected_delivery_date": datetime(2026, 6, 8, 17, 0),
        "actual_delivery_date": datetime(2026, 6, 7, 16, 45),
        "status": "Delivered",
        "rush_charge": Decimal("200.00"),  # Rush charge order 1
        "delivery_address": "88 Ayala Ave., San Lorenzo, Makati City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Standup Pouch",
                "finish_type": "Matte",
                "size": "5x8 inches",
                "quantity": 300,
                "unit_price": Decimal("8.00"),
                "discount": Decimal("0.00"),
                "design_file_path": "designs/order_005_standup.pdf",
            },
        ],
    },
    {
        "order_idx": 6,
        "customer_idx": 5,  # Christian Dale Rivera
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 6, 15, 13, 10),
        "expected_delivery_date": datetime(2026, 6, 22, 17, 0),
        "actual_delivery_date": None,
        "status": "Cancelled",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "15 J.P. Laurel Ave., Bajada, Davao City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Flyer / Brochure",
                "finish_type": "Glossy",
                "size": "A4",
                "quantity": 500,
                "unit_price": Decimal("3.50"),
                "discount": Decimal("150.00"),
                "design_file_path": "designs/order_006_flyers.pdf",
            },
        ],
    },
    {
        "order_idx": 7,
        "customer_idx": 6,  # Katrina Mae Garcia
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 6, 25, 15, 30),
        "expected_delivery_date": datetime(2026, 7, 1, 17, 0),
        "actual_delivery_date": None,
        "status": "Ready",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "202 Osmeña Blvd., Capitol Site, Cebu City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Foldable Cake Box",
                "finish_type": "Glossy",
                "size": "8x8x5 inches",
                "quantity": 80,
                "unit_price": Decimal("28.00"),
                "discount": Decimal("40.00"),
                "design_file_path": "designs/order_007_cakebox.pdf",
            },
        ],
    },

    # Month 4: July 2026
    {
        "order_idx": 8,
        "customer_idx": 7,  # John Paul Lim
        "order_type": "LayoutOnly",
        "order_date": datetime(2026, 7, 12, 10, 0),
        "expected_delivery_date": datetime(2026, 7, 15, 17, 0),
        "actual_delivery_date": None,
        "status": "Paid",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "Digital File Email Delivery",
        "is_design_fee_deducted": False,
        "items": [],
        "override_total": Decimal("750.00"),
    },
    {
        "order_idx": 9,
        "customer_idx": 8,  # Sarah Joy Hernandez
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 7, 26, 14, 0),
        "expected_delivery_date": datetime(2026, 8, 2, 17, 0),
        "actual_delivery_date": None,
        "status": "Processing",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "16 Magsaysay St., Session Rd., Baguio City",
        "is_design_fee_deducted": True,  # Design fee deducted order 1 (qty >= 100)
        "items": [
            {
                "packaging_type": "Custom Product Box",
                "finish_type": "Matte",
                "size": "Small (4x4x3)",
                "quantity": 150,
                "unit_price": Decimal("22.00"),
                "discount": Decimal("0.00"),
                "design_file_path": "designs/order_009_prodbox.pdf",
            },
        ],
    },

    # Month 5: August 2026
    {
        "order_idx": 10,
        "customer_idx": 9,  # Gabriel Mendoza
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 8, 5, 11, 25),
        "expected_delivery_date": datetime(2026, 8, 12, 17, 0),
        "actual_delivery_date": None,
        "status": "Paid",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "93 MacArthur Highway, San Fernando, Pampanga",
        "is_design_fee_deducted": True,  # Design fee deducted order 2 (qty >= 100)
        "items": [
            {
                "packaging_type": "Matte Label Stickers",
                "finish_type": "Matte",
                "size": "3x3 inches",
                "quantity": 200,
                "unit_price": Decimal("14.00"),
                "discount": Decimal("100.00"),
                "design_file_path": "designs/order_010_labels.pdf",
            },
        ],
    },
    {
        "order_idx": 11,
        "customer_idx": 0,  # Juan Dela Cruz (Returning)
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 8, 16, 9, 30),
        "expected_delivery_date": datetime(2026, 8, 19, 17, 0),
        "actual_delivery_date": None,
        "status": "Ready",
        "rush_charge": Decimal("350.00"),  # Rush charge order 2
        "delivery_address": "124 Rizal St., Brgy. Poblacion, Makati City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Food Packaging Box",
                "finish_type": "Laminated",
                "size": "Medium",
                "quantity": 100,
                "unit_price": Decimal("32.00"),
                "discount": Decimal("50.00"),
                "design_file_path": "designs/order_011_foodbox.pdf",
            },
            {
                "packaging_type": "Product Hangtags",
                "finish_type": "Matte",
                "size": "2x3 inches",
                "quantity": 100,
                "unit_price": Decimal("5.00"),
                "discount": Decimal("0.00"),
                "design_file_path": "designs/order_011_hangtag.pdf",
            },
        ],
    },
    {
        "order_idx": 12,
        "customer_idx": 2,  # Mark Joshua Bautista (Returning)
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 8, 28, 15, 0),
        "expected_delivery_date": datetime(2026, 9, 4, 17, 0),
        "actual_delivery_date": None,
        "status": "Processing",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "Lot 12 Block 5, Commonwealth, Quezon City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Kraft Paper Bag",
                "finish_type": "Plain",
                "size": "Large (10x14)",
                "quantity": 120,
                "unit_price": Decimal("18.50"),
                "discount": Decimal("20.00"),
                "design_file_path": "designs/order_012_kraftbag.pdf",
            },
        ],
    },

    # Month 6: September 2026
    {
        "order_idx": 13,
        "customer_idx": 1,  # Maria Santos (Returning)
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 9, 8, 10, 30),
        "expected_delivery_date": datetime(2026, 9, 15, 17, 0),
        "actual_delivery_date": None,
        "status": "Processing",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "77 Mabini Ave., Malate, Manila",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Glossy Sticker Sheet",
                "finish_type": "Glossy",
                "size": "A4",
                "quantity": 60,
                "unit_price": Decimal("25.00"),
                "discount": Decimal("0.00"),
                "design_file_path": "designs/order_013_stickersheet.pdf",
            },
        ],
    },
    {
        "order_idx": 14,
        "customer_idx": 4,  # Bea Alonzo Tan (Returning)
        "order_type": "LayoutOnly",
        "order_date": datetime(2026, 9, 18, 14, 45),
        "expected_delivery_date": datetime(2026, 9, 21, 17, 0),
        "actual_delivery_date": None,
        "status": "Pending",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "Digital File Email Delivery",
        "is_design_fee_deducted": False,
        "items": [],
        "override_total": Decimal("500.00"),
    },
    {
        "order_idx": 15,
        "customer_idx": 5,  # Christian Dale Rivera (Returning)
        "order_type": "ProductOrder",
        "order_date": datetime(2026, 9, 24, 16, 15),
        "expected_delivery_date": datetime(2026, 10, 1, 17, 0),
        "actual_delivery_date": None,
        "status": "Pending",
        "rush_charge": Decimal("0.00"),
        "delivery_address": "15 J.P. Laurel Ave., Bajada, Davao City",
        "is_design_fee_deducted": False,
        "items": [
            {
                "packaging_type": "Coffee Pouch with Valve",
                "finish_type": "Matte",
                "size": "250g",
                "quantity": 100,
                "unit_price": Decimal("16.50"),
                "discount": Decimal("0.00"),
                "design_file_path": "designs/order_015_coffeepouch.pdf",
            },
        ],
    },
]

# 20 Expenses across 6 months
# Categories: Labor (5), Materials (5), Miscellaneous (5), Utility (5)
EXPENSES_DATA = [
    # Month 1: April 2026
    {
        "expense_idx": 1,
        "category": "Utility",
        "amount": Decimal("2350.00"),
        "expense_date": datetime(2026, 4, 14, 16, 30),
        "description": "Meralco commercial electrical billing for print shop floor",
    },
    {
        "expense_idx": 2,
        "category": "Materials",
        "amount": Decimal("1850.00"),
        "expense_date": datetime(2026, 4, 18, 11, 15),
        "description": "Glossy photo paper bulk restock shipment (A4 230gsm)",
        "restock_material_idx": 1,  # Glossy Photo Paper
        "restock_qty": 10,
    },
    {
        "expense_idx": 3,
        "category": "Labor",
        "amount": Decimal("1200.00"),
        "expense_date": datetime(2026, 4, 25, 17, 0),
        "description": "Graphic designer overtime incentive for bulk rush layout",
    },

    # Month 2: May 2026
    {
        "expense_idx": 4,
        "category": "Materials",
        "amount": Decimal("1800.00"),
        "expense_date": datetime(2026, 5, 6, 10, 0),
        "description": "CMYK dye ink bottles restock pack",
        "restock_material_idx": 3,  # Ink Black
        "restock_qty": 4,
    },
    {
        "expense_idx": 5,
        "category": "Utility",
        "amount": Decimal("1500.00"),
        "expense_date": datetime(2026, 5, 15, 14, 30),
        "description": "PLDT enterprise business fiber internet monthly subscription",
    },
    {
        "expense_idx": 6,
        "category": "Miscellaneous",
        "amount": Decimal("750.00"),
        "expense_date": datetime(2026, 5, 22, 13, 0),
        "description": "Packaging tape rolls, bubble wrap, and cutter blades",
    },
    {
        "expense_idx": 7,
        "category": "Miscellaneous",
        "amount": Decimal("950.00"),
        "expense_date": datetime(2026, 5, 29, 15, 45),
        "description": "Local city fire safety compliance and inspection certification",
    },

    # Month 3: June 2026
    {
        "expense_idx": 8,
        "category": "Labor",
        "amount": Decimal("2500.00"),
        "expense_date": datetime(2026, 6, 8, 17, 30),
        "description": "Senior print technician mid-year performance stipend",
    },
    {
        "expense_idx": 9,
        "category": "Materials",
        "amount": Decimal("1400.00"),
        "expense_date": datetime(2026, 6, 12, 11, 20),
        "description": "Corrugated cardboard shipping boxes delivery batch",
        "restock_material_idx": 9,  # Corrugated Boxes
        "restock_qty": 50,
    },
    {
        "expense_idx": 10,
        "category": "Utility",
        "amount": Decimal("2650.00"),
        "expense_date": datetime(2026, 6, 18, 16, 0),
        "description": "Meralco electric bill for high-output digital printers",
    },
    {
        "expense_idx": 11,
        "category": "Miscellaneous",
        "amount": Decimal("680.00"),
        "expense_date": datetime(2026, 6, 26, 14, 10),
        "description": "Printer carriage lubrication oil and precision cleaner swabs",
    },

    # Month 4: July 2026
    {
        "expense_idx": 12,
        "category": "Materials",
        "amount": Decimal("1450.00"),
        "expense_date": datetime(2026, 7, 7, 10, 45),
        "description": "Matte sticker paper reams restocking batch",
        "restock_material_idx": 2,  # Matte Sticker Paper
        "restock_qty": 10,
    },
    {
        "expense_idx": 13,
        "category": "Labor",
        "amount": Decimal("1100.00"),
        "expense_date": datetime(2026, 7, 16, 17, 15),
        "description": "Helper overtime pay for heavy shipment loading and sorting",
    },
    {
        "expense_idx": 14,
        "category": "Utility",
        "amount": Decimal("620.00"),
        "expense_date": datetime(2026, 7, 24, 15, 30),
        "description": "Manila Water commercial facility monthly billing",
    },

    # Month 5: August 2026
    {
        "expense_idx": 15,
        "category": "Materials",
        "amount": Decimal("1750.00"),
        "expense_date": datetime(2026, 8, 9, 11, 0),
        "description": "Kraft paper 70gsm replenishment reams",
        "restock_material_idx": 0,  # Kraft Paper
        "restock_qty": 5,
    },
    {
        "expense_idx": 16,
        "category": "Labor",
        "amount": Decimal("1500.00"),
        "expense_date": datetime(2026, 8, 19, 18, 0),
        "description": "Night-shift print operator allowance for high-volume jobs",
    },
    {
        "expense_idx": 17,
        "category": "Miscellaneous",
        "amount": Decimal("550.00"),
        "expense_date": datetime(2026, 8, 27, 13, 40),
        "description": "Shop sanitation supplies, spray bottles, and trash bags",
    },

    # Month 6: September 2026
    {
        "expense_idx": 18,
        "category": "Utility",
        "amount": Decimal("2850.50"),
        "expense_date": datetime(2026, 9, 14, 16, 15),
        "description": "Meralco commercial electrical power billing for high-speed digital printers",
    },
    {
        "expense_idx": 19,
        "category": "Labor",
        "amount": Decimal("3000.00"),
        "expense_date": datetime(2026, 9, 21, 17, 30),
        "description": "Monthly overtime allowance for graphic designer & printing operator",
    },
    {
        "expense_idx": 20,
        "category": "Miscellaneous",
        "amount": Decimal("1200.00"),
        "expense_date": datetime(2026, 9, 26, 14, 0),
        "description": "Annual local government compliance certificates & health safety permits",
    },
]


# ---------------------------------------------------------------------------
# Seeder Implementation
# ---------------------------------------------------------------------------

class SystemSeeder:
    """Executes deterministic, foreign-key safe database seeding."""

    def __init__(self, conn, force: bool = False):
        self.conn = conn
        self.force = force

        # Mapping dictionaries from data array index to auto-increment IDs
        self.customer_ids: list[int] = []
        self.material_ids: list[int] = []
        self.order_ids: list[int] = []
        self.order_item_ids: dict[int, list[int]] = {}  # order_idx -> list of item_ids
        self.expense_ids: dict[int, int] = {}           # expense_idx -> expense_id
        self.admin_user_id: int = 1

    def run(self) -> None:
        print("\n========================================================")
        print("  AkoNi Printing Services — Complete Database Seeder   ")
        print("========================================================\n")

        init_database()

        if not self.force and not self._prompt_if_existing_data():
            print("Seeder aborted by user. No modifications were made.")
            return

        try:
            self._clean_tables()
            self._seed_users()
            self._seed_customers()
            self._seed_materials()
            self._seed_orders_and_items()
            self._seed_payments()
            self._seed_expenses()
            self._seed_stock_movements()

            self.conn.commit()
            print("\n--------------------------------------------------------")
            print("  SUCCESS: Database seeded and committed successfully!  ")
            print("--------------------------------------------------------\n")
            self._print_summary()

        except Exception as exc:
            self.conn.rollback()
            print(f"\n[ERROR] Seeding failed: {exc}")
            import traceback
            traceback.print_exc()
            raise

    # -- Safety & Cleanup -----------------------------------------------
    def _prompt_if_existing_data(self) -> bool:
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM customer_orders")
            (ord_count,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM expenses")
            (exp_count,) = cur.fetchone()
        finally:
            cur.close()

        if ord_count > 0 or exp_count > 0:
            print(f"[!] Existing data detected: {ord_count} orders, {exp_count} expenses.")
            print("    Reseeding will clean transactional tables while preserving Staff users.")
            choice = input("    Proceed with clean & reseed? [y/N]: ").strip().lower()
            return choice in ("y", "yes")
        return True

    def _clean_tables(self) -> None:
        """Truncate transactional tables in FK-safe order while preserving users."""
        print("[*] Cleaning transactional tables...")
        cur = self.conn.cursor()
        try:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for tbl in [
                "stock_movements",
                "payments",
                "order_items",
                "customer_orders",
                "expenses",
                "materials",
                "customers",
            ]:
                cur.execute(f"TRUNCATE TABLE `{tbl}`")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
            self.conn.commit()
            print("    -> Transactional tables truncated successfully.")
        finally:
            cur.close()

    # -- 1. Users -------------------------------------------------------
    def _seed_users(self) -> None:
        """Ensures admin (admin / admin123) exists. Preserves any manual Staff users."""
        print("[*] Checking Users...")
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT user_id, username, role FROM users WHERE username = 'admin'")
            admin = cur.fetchone()

            pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")

            if admin:
                self.admin_user_id = admin["user_id"]
                cur.execute(
                    "UPDATE users SET password_hash = %s, role = 'Admin', is_active = TRUE WHERE user_id = %s",
                    (pw_hash, self.admin_user_id),
                )
                print(f"    -> Updated Admin account (user_id: {self.admin_user_id}) to password 'admin123'.")
            else:
                cur.execute(
                    "INSERT INTO users (username, password_hash, first_name, last_name, role, is_active) "
                    "VALUES ('admin', %s, 'System', 'Admin', 'Admin', TRUE)",
                    (pw_hash,),
                )
                self.admin_user_id = cur.lastrowid
                print(f"    -> Created Admin account (user_id: {self.admin_user_id}) with password 'admin123'.")

            cur.execute("SELECT COUNT(*) AS total, SUM(role = 'Staff') AS staff_cnt FROM users")
            u_info = cur.fetchone()
            print(f"    -> Preserved {u_info['staff_cnt'] or 0} manual Staff user(s). Total users: {u_info['total']}.")
        finally:
            cur.close()

    # -- 2. Customers ---------------------------------------------------
    def _seed_customers(self) -> None:
        print("[*] Seeding Customers...")
        cur = self.conn.cursor()
        try:
            query = """
                INSERT INTO customers
                    (first_name, last_name, contact_number, email_address, address, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            for c in CUSTOMERS_DATA:
                cur.execute(query, (
                    c["first_name"],
                    c["last_name"],
                    c["contact_number"],
                    c["email_address"],
                    c["address"],
                    c["created_at"],
                ))
                self.customer_ids.append(cur.lastrowid)
            print(f"    -> Inserted {len(self.customer_ids)} customers.")
        finally:
            cur.close()

    # -- 3. Materials ---------------------------------------------------
    def _seed_materials(self) -> None:
        print("[*] Seeding Materials...")
        cur = self.conn.cursor()
        try:
            query = """
                INSERT INTO materials
                    (material_name, unit_of_measure, current_stock_qty, low_stock_threshold, cost_per_unit)
                VALUES (%s, %s, %s, %s, %s)
            """
            for m in MATERIALS_DATA:
                cur.execute(query, (
                    m["material_name"],
                    m["unit_of_measure"],
                    m["current_stock_qty"],
                    m["low_stock_threshold"],
                    m["cost_per_unit"],
                ))
                self.material_ids.append(cur.lastrowid)

            low_stock_cnt = sum(1 for m in MATERIALS_DATA if m["current_stock_qty"] <= m["low_stock_threshold"])
            print(f"    -> Inserted {len(self.material_ids)} materials ({low_stock_cnt} below low_stock_threshold).")
        finally:
            cur.close()

    # -- 4. Orders and Order Items --------------------------------------
    def _seed_orders_and_items(self) -> None:
        print("[*] Seeding Customer Orders and Order Items...")
        cur = self.conn.cursor()
        try:
            order_query = """
                INSERT INTO customer_orders
                    (customer_id, recorded_by_user_id, order_type, order_date,
                     expected_delivery_date, actual_delivery_date, status,
                     rush_charge, total_amount, delivery_address, is_design_fee_deducted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            item_query = """
                INSERT INTO order_items
                    (order_id, packaging_type, finish_type, size, quantity, unit_price, discount, design_file_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            for o in ORDERS_DATA:
                cust_id = self.customer_ids[o["customer_idx"]]
                is_layout = o["order_type"] == "LayoutOnly"

                # Calculate item subtotals
                item_subtotal = Decimal("0.00")
                for itm in o.get("items", []):
                    item_subtotal += (itm["quantity"] * itm["unit_price"]) - itm["discount"]

                if is_layout:
                    total_amount = o.get("override_total", Decimal("500.00"))
                else:
                    fee_deduction = Decimal("500.00") if o["is_design_fee_deducted"] else Decimal("0.00")
                    total_amount = max(Decimal("0.00"), item_subtotal + o["rush_charge"] - fee_deduction)

                cur.execute(order_query, (
                    cust_id,
                    self.admin_user_id,
                    o["order_type"],
                    o["order_date"],
                    o["expected_delivery_date"],
                    o["actual_delivery_date"],
                    o["status"],
                    o["rush_charge"],
                    total_amount,
                    o["delivery_address"],
                    o["is_design_fee_deducted"],
                ))
                order_id = cur.lastrowid
                self.order_ids.append(order_id)
                self.order_item_ids[o["order_idx"]] = []

                # Insert items if ProductOrder
                for itm in o.get("items", []):
                    cur.execute(item_query, (
                        order_id,
                        itm["packaging_type"],
                        itm["finish_type"],
                        itm["size"],
                        itm["quantity"],
                        itm["unit_price"],
                        itm["discount"],
                        itm["design_file_path"],
                    ))
                    self.order_item_ids[o["order_idx"]].append(cur.lastrowid)

            total_items = sum(len(v) for v in self.order_item_ids.values())
            print(f"    -> Inserted {len(self.order_ids)} orders (3 LayoutOnly, 12 ProductOrders) with {total_items} items.")
        finally:
            cur.close()

    # -- 5. Payments ----------------------------------------------------
    def _seed_payments(self) -> None:
        print("[*] Seeding Payments...")
        cur = self.conn.cursor()
        try:
            query = """
                INSERT INTO payments
                    (order_id, processed_by_user_id, payment_type, payment_method,
                     amount_paid, payment_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'Completed')
            """
            payments_count = 0

            # Map from order_idx to (payment_type, payment_method, amount, payment_date)
            # Payments for orders with status Paid, Processing, Ready, Delivered:
            # Order 1 (Delivered, 1500.00)
            cur.execute(query, (
                self.order_ids[0], self.admin_user_id, "ProductOrder", "Cash",
                Decimal("1500.00"), datetime(2026, 4, 10, 10, 30)
            ))
            payments_count += 1

            # Order 2 (Delivered, 1750.00): 2 payments (Assurance + Balance)
            cur.execute(query, (
                self.order_ids[1], self.admin_user_id, "Assurance", "GCash",
                Decimal("800.00"), datetime(2026, 4, 22, 14, 45)
            ))
            cur.execute(query, (
                self.order_ids[1], self.admin_user_id, "ProductOrder", "Cash",
                Decimal("950.00"), datetime(2026, 4, 27, 16, 15)
            ))
            payments_count += 2

            # Order 3 (Delivered, 2150.00)
            cur.execute(query, (
                self.order_ids[2], self.admin_user_id, "ProductOrder", "Bank Transfer",
                Decimal("2150.00"), datetime(2026, 5, 8, 11, 20)
            ))
            payments_count += 1

            # Order 4 (Paid LayoutOnly, 500.00)
            cur.execute(query, (
                self.order_ids[3], self.admin_user_id, "DesignFee", "GCash",
                Decimal("500.00"), datetime(2026, 5, 18, 16, 30)
            ))
            payments_count += 1

            # Order 5 (Delivered, 2600.00 including 200 rush): 2 payments
            cur.execute(query, (
                self.order_ids[4], self.admin_user_id, "ProductOrder", "Bank Transfer",
                Decimal("2400.00"), datetime(2026, 6, 4, 10, 0)
            ))
            cur.execute(query, (
                self.order_ids[4], self.admin_user_id, "RushFee", "Cash",
                Decimal("200.00"), datetime(2026, 6, 4, 10, 5)
            ))
            payments_count += 2

            # Order 7 (Ready, 2200.00): Full payment via 2 installments
            cur.execute(query, (
                self.order_ids[6], self.admin_user_id, "Assurance", "GCash",
                Decimal("1100.00"), datetime(2026, 6, 25, 15, 45)
            ))
            cur.execute(query, (
                self.order_ids[6], self.admin_user_id, "ProductOrder", "GCash",
                Decimal("1100.00"), datetime(2026, 7, 1, 10, 0)
            ))
            payments_count += 2

            # Order 8 (Paid LayoutOnly, 750.00)
            cur.execute(query, (
                self.order_ids[7], self.admin_user_id, "DesignFee", "Bank Transfer",
                Decimal("750.00"), datetime(2026, 7, 12, 10, 30)
            ))
            payments_count += 1

            # Order 9 (Processing, total 2800.00): Partial payment (Assurance only, remaining 1400 unpaid receivable)
            cur.execute(query, (
                self.order_ids[8], self.admin_user_id, "Assurance", "GCash",
                Decimal("1400.00"), datetime(2026, 7, 26, 14, 15)
            ))
            payments_count += 1

            # Order 10 (Paid, total 2200.00)
            cur.execute(query, (
                self.order_ids[9], self.admin_user_id, "ProductOrder", "GCash",
                Decimal("2200.00"), datetime(2026, 8, 5, 11, 40)
            ))
            payments_count += 1

            # Order 11 (Ready, total 4000.00 including 350 rush): Partial (2000 assurance + 350 rush; 1650 unpaid receivable)
            cur.execute(query, (
                self.order_ids[10], self.admin_user_id, "Assurance", "Bank Transfer",
                Decimal("2000.00"), datetime(2026, 8, 16, 9, 45)
            ))
            cur.execute(query, (
                self.order_ids[10], self.admin_user_id, "RushFee", "GCash",
                Decimal("350.00"), datetime(2026, 8, 16, 9, 50)
            ))
            payments_count += 2

            # Order 12 (Processing, total 2200.00): Partial (1100 assurance; 1100 unpaid receivable)
            cur.execute(query, (
                self.order_ids[11], self.admin_user_id, "Assurance", "Cash",
                Decimal("1100.00"), datetime(2026, 8, 28, 15, 15)
            ))
            payments_count += 1

            # Include 2 Standalone Layout-Only Payments with order_id = NULL
            cur.execute(query, (
                None, self.admin_user_id, "DesignFee", "GCash",
                Decimal("500.00"), datetime(2026, 5, 20, 11, 0)
            ))
            cur.execute(query, (
                None, self.admin_user_id, "DesignFee", "Bank Transfer",
                Decimal("500.00"), datetime(2026, 8, 22, 14, 30)
            ))
            payments_count += 2

            print(f"    -> Inserted {payments_count} payments (including 2 standalone Layout-Only payments with order_id = NULL).")
        finally:
            cur.close()

    # -- 6. Expenses ----------------------------------------------------
    def _seed_expenses(self) -> None:
        print("[*] Seeding Expenses...")
        cur = self.conn.cursor()
        try:
            query = """
                INSERT INTO expenses
                    (recorded_by_user_id, category, amount, expense_date, description)
                VALUES (%s, %s, %s, %s, %s)
            """
            for exp in EXPENSES_DATA:
                cur.execute(query, (
                    self.admin_user_id,
                    exp["category"],
                    exp["amount"],
                    exp["expense_date"],
                    exp["description"],
                ))
                self.expense_ids[exp["expense_idx"]] = cur.lastrowid
            print(f"    -> Inserted {len(self.expense_ids)} expenses across 6 months (Labor, Materials, Utility, Misc).")
        finally:
            cur.close()

    # -- 7. Stock Movements ---------------------------------------------
    def _seed_stock_movements(self) -> None:
        print("[*] Seeding Stock Movements...")
        cur = self.conn.cursor()
        try:
            query = """
                INSERT INTO stock_movements
                    (material_id, recorded_by_user_id, movement_type, quantity, reason,
                     movement_date, order_item_id, expense_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            mv_count = 0

            # 1. IN Movements (Linked to Materials Expenses)
            for exp in EXPENSES_DATA:
                if "restock_material_idx" in exp:
                    mat_id = self.material_ids[exp["restock_material_idx"]]
                    exp_id = self.expense_ids[exp["expense_idx"]]
                    cur.execute(query, (
                        mat_id,
                        self.admin_user_id,
                        "IN",
                        exp["restock_qty"],
                        f"Material restocking shipment: {exp['description']}",
                        exp["expense_date"],
                        None,
                        exp_id,
                    ))
                    mv_count += 1

            # 2. OUT Movements (Linked to ProductOrders with status Processing, Ready, Delivered)
            # Order 1 (Delivered, item 1) -> Material: Corrugated Boxes (idx 9)
            cur.execute(query, (
                self.material_ids[9],
                self.admin_user_id,
                "OUT",
                10,
                "Production and packaging fulfillment for Order #1",
                datetime(2026, 4, 11, 14, 0),
                self.order_item_ids[1][0],
                None,
            ))
            mv_count += 1

            # Order 2 (Delivered, item 1) -> Material: Kraft Paper (idx 0)
            cur.execute(query, (
                self.material_ids[0],
                self.admin_user_id,
                "OUT",
                8,
                "Production fulfillment for Order #2",
                datetime(2026, 4, 23, 11, 0),
                self.order_item_ids[2][0],
                None,
            ))
            mv_count += 1

            # Order 3 (Delivered, item 1) -> Material: Glossy Photo Paper (idx 1)
            cur.execute(query, (
                self.material_ids[1],
                self.admin_user_id,
                "OUT",
                15,
                "Production printing fulfillment for Order #3",
                datetime(2026, 5, 9, 13, 30),
                self.order_item_ids[3][0],
                None,
            ))
            mv_count += 1

            # Order 5 (Delivered, item 1) -> Material: Packaging Tape (idx 7)
            cur.execute(query, (
                self.material_ids[7],
                self.admin_user_id,
                "OUT",
                4,
                "Rush order packaging sealing for Order #5",
                datetime(2026, 6, 5, 10, 0),
                self.order_item_ids[5][0],
                None,
            ))
            mv_count += 1

            # Order 7 (Ready, item 1) -> Material: Corrugated Boxes (idx 9)
            cur.execute(query, (
                self.material_ids[9],
                self.admin_user_id,
                "OUT",
                12,
                "Order fulfillment assembly for Order #7",
                datetime(2026, 6, 26, 15, 0),
                self.order_item_ids[7][0],
                None,
            ))
            mv_count += 1

            # Order 9 (Processing, item 1) -> Material: Matte Sticker Paper (idx 2)
            cur.execute(query, (
                self.material_ids[2],
                self.admin_user_id,
                "OUT",
                15,
                "In-progress production batch for Order #9",
                datetime(2026, 7, 27, 10, 30),
                self.order_item_ids[9][0],
                None,
            ))
            mv_count += 1

            # Order 11 (Ready, item 1) -> Material: Corrugated Boxes (idx 9)
            cur.execute(query, (
                self.material_ids[9],
                self.admin_user_id,
                "OUT",
                14,
                "Rush order completed assembly for Order #11",
                datetime(2026, 8, 17, 11, 20),
                self.order_item_ids[11][0],
                None,
            ))
            mv_count += 1

            # Order 12 (Processing, item 1) -> Material: Kraft Paper (idx 0)
            cur.execute(query, (
                self.material_ids[0],
                self.admin_user_id,
                "OUT",
                12,
                "Active printing run for Order #12",
                datetime(2026, 8, 29, 14, 0),
                self.order_item_ids[12][0],
                None,
            ))
            mv_count += 1

            # 3. 1 ADJUSTMENT Movement (Inventory Correction)
            # Material: Ink Cyan (idx 4)
            cur.execute(query, (
                self.material_ids[4],
                self.admin_user_id,
                "ADJUSTMENT",
                -2,
                "Quarterly physical stock audit spill damage deduction",
                datetime(2026, 8, 30, 16, 45),
                None,
                None,
            ))
            mv_count += 1

            print(f"    -> Inserted {mv_count} stock movements (5 IN restocks, 8 OUT orders, 1 ADJUSTMENT).")
        finally:
            cur.close()

    # -- Summary Output -------------------------------------------------
    def _print_summary(self) -> None:
        cur = self.conn.cursor(dictionary=True)
        try:
            print("Database Record Count Summary:")
            print("--------------------------------------------------")
            tables = [
                ("users", "Users (Admin + Staff)"),
                ("customers", "Customers"),
                ("materials", "Materials (Inventory)"),
                ("customer_orders", "Customer Orders"),
                ("order_items", "Order Line Items"),
                ("payments", "Payments (Collections)"),
                ("expenses", "Expenses (Disbursements)"),
                ("stock_movements", "Stock Movements (IN/OUT/ADJ)"),
            ]
            for tbl, desc in tables:
                cur.execute(f"SELECT COUNT(*) AS c FROM `{tbl}`")
                cnt = cur.fetchone()["c"]
                print(f"  {desc:<34} : {cnt:>4} rows")
            print("--------------------------------------------------")
            print("Admin credentials : admin / admin123")
            print("Status            : Ready for application login & test run.\n")
        finally:
            cur.close()


def main():
    parser = argparse.ArgumentParser(description="AkoNi Printing Services Database Seeder")
    parser.add_argument("--clean", action="store_true", help="Automatically clean transactional tables and reseed")
    parser.add_argument("--force", action="store_true", help="Non-interactive force reseed")
    args = parser.parse_args()

    conn = get_connection()
    try:
        seeder = SystemSeeder(conn, force=args.clean or args.force)
        seeder.run()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
