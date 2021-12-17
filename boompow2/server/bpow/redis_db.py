#!/usr/bin/env python3

import asyncio
import aioredis


SERVICE_PUBLIC = "Y"

class BpowRedis(object):

    def __init__(self, server, loop):
        self.pool = aioredis.create_pool(
            server,
            minsize=5, maxsize=15,
            loop=loop,
            db=3
        )

    async def setup(self):
        self.pool = await self.pool

    async def close(self):
        self.pool.close()
        await self.pool.wait_closed()

    async def get_payment_factor(self):
        payment_factor = await self.get("bpow:paymentfactor")
        return float(payment_factor) if payment_factor is not None else 0

    async def get_total_paid(self):
        total_paid = await self.get('bpow:totalrewards')
        return float(total_paid) if total_paid is not None else 0

    async def all_statistics(self):
        precache_total = await self.get("stats:precache")
        on_demand_total = await self.get("stats:ondemand")
        precache_total = precache_total if precache_total is not None else 0
        on_demand_total = on_demand_total if on_demand_total is not None else 0

        public_services = list()
        private_services = {"count": 0, "precache": 0, "ondemand": 0}
        services = await self.set_members("services")
        for service in services:
            info = await self.hash_getmany(f"service:{service}", "public", "display", "website", "precache", "ondemand")
            info["precache"] = int(info["precache"])
            info["ondemand"] = int(info["ondemand"])
            is_public = info.pop("public") == SERVICE_PUBLIC
            if is_public:
                info['user_name'] = service
                public_services.append(info)
            else:
                private_services["count"] += 1
                private_services["precache"] += info["precache"]
                private_services["ondemand"] += info["ondemand"]
        return dict(
            total_paid_banano = await self.get_total_paid(),
            payment_factor_banano = await self.get_payment_factor(),
            services = {
                "public": public_services,
                "private": private_services
            },
            work = {
                "precache": int(precache_total),
                "ondemand": int(on_demand_total)
            }
        )

    async def get_percent_of_total(self, in_client: str) -> float:
        """Get what % this client has contributed towards the overall total"""
        clients = await self.set_members("clients")
        clients = {c for c in clients}
        total_pow = 0 # Total of all clients
        this_client = None # total this client has done
        for client in clients:
            client_info = await self.hash_getall(f"client:{client}")
            if not client_info:
                continue
            # Sum total work contributions
            total_works = 0
            total_works += int(client_info['precache']) if 'precache' in client_info else 0
            total_works += int(client_info['ondemand']) if 'ondemand' in client_info else 0
            # Get how many pows this client has already been paid for
            total_credited = int(client_info['total_credited']) if 'total_credited' in client_info else 0

            # Get how many this client has done in this cycle
            should_be_credited = total_works - total_credited
            total_pow += should_be_credited
            if client == in_client:
                this_client = should_be_credited
        if this_client is None:
            return None
        return round((this_client / total_pow), 6)

    async def insert(self, key: str, value: str):
        return await self.pool.execute('set', key, value )

    async def insert_expire(self, key: str, value: str, seconds: int):
        return await self.pool.execute('setex', key, seconds, value)

    async def insert_if_noexist(self, key: str, value: str):
        """Returns True if the key was inserted, False if it was already there"""
        key_set = await self.pool.execute('setnx', key, value)
        return key_set == 1

    async def insert_if_noexist_expire(self, key: str, value: str, seconds: int):
        """Returns True if the key was inserted, False if it was already there"""
        key_set = await self.pool.execute('setnx', key, value)
        if key_set == 1:
            await self.pool.execute('expire', key, seconds)
        return key_set == 1

    async def delete(self, key: str):
        return await self.pool.execute('del', key)

    async def get(self, key: str):
        val = await self.pool.execute('get', key)
        return val.decode("utf-8") if val else None

    async def exists(self, key: str):
        exists = await self.pool.execute('exists', key)
        return exists == 1

    async def increment(self, key: str):
        return await self.pool.execute('incr', key)

    async def hash_increment(self, key: str, field: str, by=1):
        return await self.pool.execute('hincrby', key, field, by)

    async def hash_getall(self, key: str):
        arr = await self.pool.execute('hgetall', key)
        return {arr[i].decode("utf-8"): arr[i+1].decode("utf-8") for i in range(0, len(arr)-1, 2)}

    async def hash_getmany(self, key, *fields, decode=True):
        arr = await self.pool.execute('hmget', key, *fields)
        return_dict = {}
        for i in range(len(arr)):
            if arr[i] is not None:
                return_dict[fields[i]] = arr[i].decode("utf-8")
            else:
                return_dict[fields[i]] = 0
        return return_dict

    async def hash_setmany(self, key, fields):
        for fkey in fields:
            await self.pool.execute('hmset', key, fkey, fields[fkey])
        return

    async def hash_get(self, key: str, field: str):
        return await self.pool.execute('hget', key, field)

    async def set_add(self, key: str, value: str):
        return await self.pool.execute('sadd', key, value)

    async def set_members(self, key: str):
        members = await self.pool.execute('smembers', key)
        return {member.decode("utf-8") for member in members}

    async def set_remove(self, key: str, value: str):
        return await self.pool.execute('srem', key, value)