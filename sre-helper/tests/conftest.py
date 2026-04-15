try:
    import nest_asyncio
except ModuleNotFoundError:
    nest_asyncio = None

if nest_asyncio is not None:
    nest_asyncio.apply()
