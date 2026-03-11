from datetime import timedelta
from ..db.base.database_manager import DatabaseManager
from ..utils.stock_calculator import StockCalculatorService
from ..models.device_model import Device
from ..models.item_model import Item
from ..models.inventory_model import Inventory, WeightTracking, ActivityLog
from ..schemas.inventory_schema import (
    InventoryCreate,
    InventoryUpdate,
    InventoryRead
)
from ..utils.logger import get_logger
from ..utils.timezone import ist_now

logger = get_logger(__name__)


class InventoryManager:
    def __init__(self, db_type: str):
        self.db_manager = DatabaseManager(db_type)
        self.stock_service = StockCalculatorService(db_type)
        self.weight_tracker = WeightTrackingManager(db_type)
        self.activity_logger = ActivityLogManager(db_type)

    async def _log_activity(self, device_id: int, event: str):
        try:
            await self.activity_logger.create(device_id, event)
        except Exception as e:
            logger.warning(f"Failed to log activity for device {device_id}: {e}")

    # ----------------------------------
    # INTERNAL CALCULATION
    # ----------------------------------
    def _calculate(self, inv, item):
        weight = inv.Weight or 0
        per_unit = item.PerUnitWeight or 1

        # Stock
        if item.Measurement == "Gram":
            stock = weight
        else:
            stock = round(weight / per_unit)

        # StockOut (days)
        stock_out = None
        if item.MinThreshold and stock > 0:
            stock_out = int(stock / item.MinThreshold)

        # Status
        if stock == 0:
            status = "NoStock"
        elif stock < item.MinThreshold:
            status = "LowStock"
        elif stock > item.MaxThreshold:
            status = "OverStock"
        else:
            status = "InStock"

        return stock, stock_out, status

    async def create_inventory(self, data: InventoryCreate) -> dict:
        try:
            await self.db_manager.connect()
            obj = await self.db_manager.create(Inventory, data.dict())

            return {
                "success": True,
                "message": "Inventory created successfully",
                "data": InventoryRead.from_orm(obj).dict()
            }
        finally:
            await self.db_manager.disconnect()

    async def get_inventory(self, inventory_id: int) -> dict:
        try:
            await self.db_manager.connect()
            result = await self.db_manager.read(
                Inventory, {"InventoryId": inventory_id}
            )

            if not result:
                return {"success": False, "message": "Inventory not found", "data": None}

            return {
                "success": True,
                "message": "Inventory fetched successfully",
                "data": InventoryRead.from_orm(result[0]).dict()
            }
        finally:
            await self.db_manager.disconnect()

    async def get_all_inventory(self) -> dict:
        try:
            await self.db_manager.connect()
            inventories = await self.db_manager.read(Inventory)

            return {
                "success": True,
                "message": "Inventory list fetched successfully",
                "data": [InventoryRead.from_orm(i).dict() for i in inventories]
            }
        finally:
            await self.db_manager.disconnect()

    async def update_inventory(self, inventory_id: int, data: InventoryUpdate) -> dict:
        try:
            await self.db_manager.connect()
            update_data = data.dict(exclude_unset=True)

            rows = await self.db_manager.update(
                Inventory,
                {"InventoryId": inventory_id},
                update_data
            )

            return {
                "success": bool(rows),
                "message": "Inventory updated successfully" if rows else "Inventory not found",
                "data": {"rows_affected": rows}
            }
        finally:
            await self.db_manager.disconnect()

    async def delete_inventory(self, inventory_id: int) -> dict:
        try:
            await self.db_manager.connect()
            rows = await self.db_manager.delete(
                Inventory, {"InventoryId": inventory_id}
            )

            return {
                "success": bool(rows),
                "message": "Inventory deleted successfully" if rows else "Inventory not found",
                "data": {"rows_affected": rows}
            }
        finally:
            await self.db_manager.disconnect()

    # async def update_weight_by_device(self, device_id: int, weight: float) -> dict:
    #     """
    #     Update inventory weight based on deviceId
    #     """
    #     try:
    #         await self.db_manager.connect()
    #         rows = await self.db_manager.update(
    #             Inventory,
    #             {"DeviceId": device_id},
    #             {"Weight": weight}
    #         )

    #         return {
    #             "success": bool(rows),
    #             "message": "Weight updated successfully" if rows else "No inventory linked to device",
    #             "data": {"rows_affected": rows}
    #         }
    #     finally:
    #         await self.db_manager.disconnect()

    async def update_weight_by_device(self, device_id: int, weight: float) -> dict:
        try:
            await self.db_manager.connect()

            # Fetch device
            device = await self.db_manager.read(Inventory, {"DeviceId": device_id})
            if not device:
                return {
                    "success": False,
                    "message": "Device not found",
                    "data": None
                }

            device = device[0]

            # ---------------------------
            # UPDATE DEVICE
            # ---------------------------
            await self.db_manager.update(
                Inventory,
                {"DeviceId": device_id},
                {
                    "Weight": weight
                }
            )

            logger.info(
                f"Device {device_id} updated | "
                f"Weight={weight}"
            )

            # ---------------------------
            # SAVE WEIGHT HISTORY
            # ---------------------------
            await self.weight_tracker.create(device_id, weight)

            # ---------------------------
            # LOG ACTIVITY
            # ---------------------------
            await self._log_activity(
                device_id,
                f"Weight updated {weight}"
            )

            # ---------------------------
            # TRIGGER STOCK RECALC
            # ---------------------------
            # await self.stock_service.update_stock_by_device(device_id)

            return {
                "success": True,
                "message": "Device weight updated, logged, and stock recalculated",
                "data": {
                    "DeviceId": device_id,
                    "Weight": weight
                }
            }

        except Exception as e:
            logger.error(f"Error updating device weight {device_id}: {e}")
            return {
                "success": False,
                "message": f"Error updating device weight: {e}",
                "data": None
            }

        finally:
            await self.db_manager.disconnect()


    
    # ----------------------------------
    # GET ALL INVENTORY INFO
    # ----------------------------------
    async def get_inventory_info(self) -> dict:
        try:
            await self.db_manager.connect()

            inventories = await self.db_manager.read(Inventory)
            items = await self.db_manager.read(Item)
            devices = await self.db_manager.read(Device)

            item_map = {i.ItemId: i for i in items}
            device_map = {d.DeviceId: d for d in devices}

            result = []

            for inv in inventories:
                item = item_map.get(inv.ItemId)
                device = device_map.get(inv.DeviceId)

                if not item:
                    continue

                stock, stock_out, status = self._calculate(inv, item)

                result.append({
                    "InventoryId": inv.InventoryId,

                    "ItemId": item.ItemId,
                    "ItemName": item.ItemName,
                    "Category": item.Category,
                    "Description": item.Description,
                    "PerUnitWeight": item.PerUnitWeight,
                    "Weight": inv.Weight,

                    "DeviceId": device.DeviceId if device else None,
                    "DeviceName": device.DeviceName if device else None,
                    "LocationName": device.LocationName if device else None,

                    "Stock": stock,
                    "StockOut": stock_out,
                    "Consumption": item.MinThreshold,
                    "Status": status,

                    "CreatedAt": inv.CreatedAt,
                    "UpdatedAt": inv.UpdatedAt
                })

            return {
                "success": True,
                "message": "Inventory info fetched successfully",
                "data": result
            }

        except Exception as e:
            return {"success": False, "message": str(e), "data": None}
        finally:
            await self.db_manager.disconnect()

    # ----------------------------------
    # GET SINGLE INVENTORY INFO
    # ----------------------------------
    async def get_inventory_info_by_id(self, inventory_id: int) -> dict:
        try:
            await self.db_manager.connect()

            inv = await self.db_manager.read(Inventory, {"InventoryId": inventory_id})
            if not inv:
                return {"success": False, "message": "Inventory not found", "data": None}

            inv = inv[0]
            item = (await self.db_manager.read(Item, {"ItemId": inv.ItemId}))[0]

            device = None
            if inv.DeviceId:
                d = await self.db_manager.read(Device, {"DeviceId": inv.DeviceId})
                device = d[0] if d else None

            stock, stock_out, status = self._calculate(inv, item)

            return {
                "success": True,
                "message": "Inventory info fetched successfully",
                "data": {
                    "InventoryId": inv.InventoryId,

                    "ItemId": item.ItemId,
                    "ItemName": item.ItemName,
                    "Category": item.Category,
                    "Description": item.Description,
                    "PerUnitWeight": item.PerUnitWeight,
                    "Weight": inv.Weight,

                    "DeviceId": device.DeviceId if device else None,
                    "DeviceName": device.DeviceName if device else None,
                    "LocationName": device.LocationName if device else None,

                    "Stock": stock,
                    "StockOut": stock_out,
                    "Consumption": item.MinThreshold,
                    "Status": status,

                    "CreatedAt": inv.CreatedAt,
                    "UpdatedAt": inv.UpdatedAt
                }
            }

        except Exception as e:
            return {"success": False, "message": str(e), "data": None}
        finally:
            await self.db_manager.disconnect()




# ------------------------
# DEVICE TRACKING
# ------------------------


class WeightTrackingManager:
    def __init__(self, db_type: str):
        self.db = DatabaseManager(db_type)

    async def create(self, device_id: int, weight: float):
        await self.db.connect()
        obj = await self.db.create(
            WeightTracking,
            {"DeviceId": device_id, "Weight": weight}
        )
        await self.db.disconnect()
        return obj

    async def get(self, device_id: int, filter_by: str = None):
        await self.db.connect()

        filters = {"DeviceId": device_id}
        data = await self.db.read(WeightTracking, filters)

        if filter_by:
            now = ist_now()
            delta = {
                "day": 1,
                "week": 7,
                "month": 30
            }.get(filter_by)

            if delta:
                data = [
                    d for d in data
                    if d.DateTime >= now - timedelta(days=delta)
                ]

        data.sort(key=lambda x: x.DateTime, reverse=True)
        await self.db.disconnect()
        return data

    async def delete_by_device(self, device_id: int):
        await self.db.connect()
        rows = await self.db.delete(
            WeightTracking,
            {"DeviceId": device_id}
        )
        await self.db.disconnect()
        return rows

    async def clear(self):
        await self.db.connect()
        rows = await self.db.execute_raw(
            "DELETE FROM WeightTracking"
        )
        await self.db.disconnect()
        return rows
    



class ActivityLogManager:
    def __init__(self, db_type: str):
        self.db = DatabaseManager(db_type)

    async def create(self, device_id: int, event: str):
        await self.db.connect()
        obj = await self.db.create(
            ActivityLog,
            {"DeviceId": device_id, "Event": event}
        )
        await self.db.disconnect()
        return obj

    async def get(self, device_id: int, filter_by: str = None):
        await self.db.connect()

        logs = await self.db.read(ActivityLog, {"DeviceId": device_id})

        if filter_by:
            now = ist_now()
            delta = {"day": 1, "week": 7, "month": 30}.get(filter_by)
            if delta:
                logs = [
                    l for l in logs
                    if l.DateTime >= now - timedelta(days=delta)
                ]

        logs.sort(key=lambda x: x.DateTime, reverse=True)
        await self.db.disconnect()
        return logs

    async def delete_by_device(self, device_id: int):
        await self.db.connect()
        rows = await self.db.delete(ActivityLog, {"DeviceId": device_id})
        await self.db.disconnect()
        return rows

    async def clear(self):
        await self.db.connect()
        await self.db.execute_raw("DELETE FROM ActivityLog")
        await self.db.disconnect()




# from ..utils.logger import get_logger
# from ..db.base.database_manager import DatabaseManager
# from ..models.inventory_model import Inventory
# from ..models.device_model import Device
# from ..schemas.inventory_schema import (
#     InventoryCreate,
#     InventoryUpdate,
#     InventoryRead,
#     StockUpdate,
#     DeviceAssign
# )

# logger = get_logger(__name__)


# class InventoryManager:
#     def __init__(self, db_type: str):
#         self.db_manager = DatabaseManager(db_type)

#     # ------------------------
#     # INVENTORY CRUD
#     # ------------------------

#     async def create_inventory(self, inv: InventoryCreate) -> dict:
#         try:
#             await self.db_manager.connect()
#             obj = await self.db_manager.create(Inventory, inv.dict())

#             return {
#                 "success": True,
#                 "message": "Inventory created successfully",
#                 "data": InventoryRead.from_orm(obj).dict()
#             }
#         finally:
#             await self.db_manager.disconnect()

#     async def get_inventory(self, inventory_id: int) -> dict:
#         try:
#             await self.db_manager.connect()

#             inventories = await self.db_manager.read(
#                 Inventory,
#                 {"InventoryId": inventory_id}
#             )

#             if not inventories:
#                 return {
#                     "success": False,
#                     "message": "Inventory not found",
#                     "data": None
#                 }

#             inventory = inventories[0]

#             device = None
#             if inventory.DeviceId:
#                 devices = await self.db_manager.read(
#                     Device,
#                     {"DeviceId": inventory.DeviceId}
#                 )
#                 device = devices[0] if devices else None

#             response_data = {
#                 "InventoryId": inventory.InventoryId,
#                 "ItemCode": inventory.ItemCode,
#                 "ItemName": inventory.ItemName,
#                 "Category": inventory.Category,
#                 "Description": inventory.Description,

#                 "Device": {
#                     "DeviceId": device.DeviceId,
#                     "DeviceName": device.DeviceName,
#                     "LastReading": device.LastReading,
#                     "Weight": device.Weight,
#                     "LocationName": device.LocationName,
#                 } if device else None,

#                 "UnitWeight": inventory.UnitWeight,
#                 "Stock": inventory.Stock,
#                 "Threshold": inventory.Threshold,
#                 "StockOut": inventory.StockOut,
#                 "Consumption": inventory.Consumption,
#                 "Status": inventory.Status,
#                 "CreatedAt": inventory.CreatedAt,
#                 "UpdatedAt": inventory.UpdatedAt
#             }

#             return {
#                 "success": True,
#                 "message": "Inventory fetched successfully",
#                 "data": response_data
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": f"Error fetching inventory: {e}",
#                 "data": None
#             }

#         finally:
#             await self.db_manager.disconnect()


#     async def get_all_inventory(self) -> dict:
#         try:
#             await self.db_manager.connect()

#             inventories = await self.db_manager.read(Inventory)
#             devices = await self.db_manager.read(Device)

#             # Device lookup by DeviceId
#             device_map = {d.DeviceId: d for d in devices}

#             inventory_list = []

#             total_items = 0
#             low_stock = 0
#             out_of_stock = 0
#             linked_devices = 0

#             for inv in inventories:
#                 total_items += 1

#                 stock = inv.Stock or 0
#                 status = inv.Status
#                 device = device_map.get(inv.DeviceId)

#                 # -------------------------
#                 # COUNTS BASED ON STORED STATUS
#                 # -------------------------
#                 if status == "LowStock":
#                     low_stock += 1
#                 elif status == "OutOfStock":
#                     out_of_stock += 1

#                 if device:
#                     linked_devices += 1

#                 inventory_list.append({
#                     "InventoryId": inv.InventoryId,
#                     "ItemCode": inv.ItemCode,
#                     "ItemName": inv.ItemName,
#                     "Category": inv.Category,
#                     "Description": inv.Description,

#                     "Device": {
#                         "DeviceId": device.DeviceId,
#                         "DeviceName": device.DeviceName,
#                         "LastReading": device.LastReading,
#                         "Weight": device.Weight,
#                         "LocationName": device.LocationName,
#                     } if device else None,

#                     "UnitWeight": inv.UnitWeight,
#                     "Stock": stock,
#                     "Threshold": inv.Threshold,
#                     "StockOut": inv.StockOut,
#                     "Consumption": inv.Consumption,
#                     "Status": status,
#                     "CreatedAt": inv.CreatedAt,
#                     "UpdatedAt": inv.UpdatedAt
#                 })

#             return {
#                 "success": True,
#                 "message": "Inventory fetched successfully",
#                 "data": {
#                     "TotalItems": total_items,
#                     "LowStock": low_stock,
#                     "OutOfStock": out_of_stock,
#                     "LinkedDevices": linked_devices,
#                     "InventoryData": inventory_list
#                 }
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": f"Error fetching inventory: {e}",
#                 "data": None
#             }

#         finally:
#             await self.db_manager.disconnect()


#     async def update_inventory(self, inventory_id: int, data: InventoryUpdate) -> dict:
#         try:
#             await self.db_manager.connect()
#             rowcount = await self.db_manager.update(
#                 Inventory,
#                 {"InventoryId": inventory_id},
#                 data.dict(exclude_unset=True)
#             )

#             if rowcount:
#                 return {
#                     "success": True,
#                     "message": "Inventory updated successfully",
#                     "data": {"rows_affected": rowcount}
#                 }

#             return {"success": False, "message": "Inventory not found"}
#         finally:
#             await self.db_manager.disconnect()

#     async def delete_inventory(self, inventory_id: int) -> dict:
#         try:
#             await self.db_manager.connect()
#             rowcount = await self.db_manager.delete(Inventory, {"InventoryId": inventory_id})

#             if rowcount:
#                 return {
#                     "success": True,
#                     "message": "Inventory deleted successfully",
#                     "data": {"rows_affected": rowcount}
#                 }

#             return {"success": False, "message": "Inventory not found"}
#         finally:
#             await self.db_manager.disconnect()

#     # ------------------------
#     # BUSINESS OPERATIONS
#     # ------------------------

#     async def update_stock(self, inventory_id: int, data: StockUpdate) -> dict:
#         return await self.update_inventory(inventory_id, StockUpdate(**data.dict()))

#     async def assign_device(self, inventory_id: int, data: DeviceAssign) -> dict:
#         return await self.update_inventory(inventory_id, DeviceAssign(DeviceId=data.DeviceId))

#     async def get_by_device(self, device_id: int) -> dict:
#         try:
#             await self.db_manager.connect()
#             items = await self.db_manager.read(Inventory, {"DeviceId": device_id})

#             return {
#                 "success": True,
#                 "message": "Inventory fetched by device",
#                 "data": [InventoryRead.from_orm(i).dict() for i in items]
#             }
#         finally:
#             await self.db_manager.disconnect()
