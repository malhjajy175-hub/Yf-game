import os
import motor.motor_asyncio

MONGODB_URI = os.getenv("MONGODB_URI")

_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
_db = _client["yfgame"]
_collection = _db["points"]


def get_collection():
    return _collection


async def get_points(user_id: int) -> dict:
    try:
        doc = await _collection.find_one({"user_id": user_id})
        if not doc:
            return {"solo": 0, "group": 0}
        return {"solo": doc.get("solo", 0), "group": doc.get("group", 0)}
    except Exception as e:
        print(f"⚠️ get_points error: {e}")
        return {"solo": 0, "group": 0}


async def add_solo_points(user_id: int, amount: int = 1):
    try:
        await _collection.update_one(
            {"user_id": user_id},
            {"$inc": {"solo": amount}},
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ add_solo_points error: {e}")


async def add_group_points(user_id: int, amount: int = 1):
    try:
        await _collection.update_one(
            {"user_id": user_id},
            {"$inc": {"group": amount}},
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ add_group_points error: {e}")


async def transfer_points(from_id: int, to_id: int, amount: int) -> bool:
    try:
        # تأكد إن المستخدم عنده document أولاً
        await _collection.update_one(
            {"user_id": from_id},
            {"$setOnInsert": {"solo": 0, "group": 0}},
            upsert=True
        )

        from_pts = await get_points(from_id)
        solo = from_pts["solo"]
        group = from_pts["group"]
        total = solo + group

        if total < amount:
            return False

        if solo >= amount:
            result = await _collection.update_one(
                {"user_id": from_id, "solo": {"$gte": amount}},
                {"$inc": {"solo": -amount}}
            )
        else:
            remaining = amount - solo
            result = await _collection.update_one(
                {"user_id": from_id, "solo": solo, "group": {"$gte": remaining}},
                {"$set": {"solo": 0}, "$inc": {"group": -remaining}}
            )

        if result.modified_count == 0:
            return False

        await _collection.update_one(
            {"user_id": to_id},
            {"$inc": {"solo": amount}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"⚠️ transfer_points error: {e}")
        return False
        
