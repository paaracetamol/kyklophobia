# kyklophobia

recreation of beta Minecraft in pure* python
NOT affiliated with mojang

```
make run
make server

# or

python3.11 launch.py
python3.11 server.py
```

**OLD** demo video: https://www.youtube.com/watch?v=o_IDO01NylM
| | |
|---|---|
| <img width="1598" height="898" alt="image" src="https://github.com/user-attachments/assets/bd2d3750-bd5b-4125-910e-9e6774a14e4c" /> | <img width="1601" height="900" alt="image" src="https://github.com/user-attachments/assets/2409f418-ea9b-4f53-bfb4-d800f6211943" /> |
| <img width="1607" height="901" alt="image" src="https://github.com/user-attachments/assets/f03f35ff-7676-4691-aba3-8c18c7b37c4f" /> | <img width="1603" height="901" alt="image" src="https://github.com/user-attachments/assets/38ae0a7e-8841-41e5-9d67-58b46f2c3dec" /> |


root `launch.py` & `server.py` are shim -> `client/launch.py`, `server/server.py`. gamefiles in `/content`


## install

`requires python 3.11+`

**makefile**
```
make run
make server
```

**uv (manual)**

```
uv sync
uv run launch.py
uv run server.py
```

**pip**

```
python3.11 -m venv venv
source venv/bin/activate  # windows
venv\Scripts\activate     # linux

pip install -r requirements.txt
python launch.py
```

**headless server**

```
python3.11 server.py --host 0.0.0.0 --port 25250 \
                     --world default --seed 12345 \
                     --max-players 20 
```


## first launch

First launch is **SLOW**. 
numba compiles `_generate`, `bakelight`, `build_meshjit` + a pile of smaller jit on
first run, cache per-world in `saves/<world>/cache` (via `NUMBA_CACHE_DIR`). subsequent
launches of that world fine. each world keeps its own cache so loading a second world
doesnt evict the first

> [!NOTE] 
> if world doesnt render, double esc (exit) and reload. fps also bad on first few run


## layout

```
game/
├── launch.py
├── server.py
├── client/
│   ├── lscreens.py         menus lists
│   ├── lwidgets.py
│   ├── lconst.py
│   ├── ldata.py
│   ├── lplayer.py
│   ├── resourcepacks/      textures models animations
│   └── saves/
├── content/
│   ├── main.py             VoxelWorld, owns all
│   ├── config.py«
│   ├── keys.py             input configs
│   ├── engine/             camera, physics, particles, sound, lightmap, gamma
│   ├── world/              gen, chunk, mesh, blocks, anim, renderers/, states/
│   ├── entity/             core + ai/, player/, blockenty/, item/
│   └── ui/                 network/  commands/  items/  shaders/
└── server/
    ├── server.py
    └── instance.py
```

`server/` is NOT a duplicate of `content/` anymore. 


## voxels

chunk = `(16, 128, 16) uint16`

```
bit  15  14 13 12 11 10  9 8 7 6 5 4 3 2 1 0
     F   S  S  S  S  S   I I I I I I I I I I
     |   \___________/   \_________________/
     |    5b state         10b block id (0x3FF, 1024 ids)
     mod-flag (playermade)
```


light = 2 separate `(16,128,16) uint8` arrays


## chunk generation

```
load_chunk(cx,cz)
     │
     ▼
queue_chunkbuild ──► mesh_builder_thread pop, dist sort -> player
     │               in-flight cap = genworkers*2
     ▼
 (parallel)
terrain_executor     client
     │               server
     │
     ├── _generate()                                    world/generate.py
     │     1a  climate+biome on 5² grid : 1 sample every 4 b
     │     1b  density field, 5 * 17 * 5
     │     2   trilinear interp -> 16*128*16, dens > 0 = solid
     │     2b  cave carve, 2 noise field, repelled from water column
     │     3   surface cap p biome, sea level, badlands band, ice
     │
     ├── decorators
     │
     ├── pending_decorations[cx,cz]
     ├── applymods()
     └── gen_ready = True
     │
     ▼
bakelight()  ──► mesh_build_queue
     │
     ▼
build_meshjit()
     │
     ▼
queue_meshupload ──► main thread, 4ms/frame, 4-6 chunk -> upload_mesh()
```


### caves

carved last. 
two independent 3d noise field, a cell is dug when
`n1² + n2² < threshold²` := the intersection of two noise shell.
threshold falls off with height (y<95=nothing) and is scaled down near any
column that contain water.


## lighting

2 channel, both 0-15 BFS flood (njit): `bakelight()`

```
   sky[16,128,16] u8                     blk[16,128,16] u8
   ──────────────────                    ──────────────────
   seed top down p column,               seed every emitter cell,
   15 - BLOCK_OPAC[id] as it             BLOCK_EMIT[id]
   descend, stop = 0 
          │                                       │
          └──────── _seedneighb() ────────────────┘
                          │
                          ▼
                    _flood() BFS

```

-> mesher -> vertex colour. 
`_corners()` take 4 corner of a face -> averaged 2^3 cell around each

```
vert = 3f pos | 3f lit | 2f uv        <- 8 float, 6 vert/face, nonidx

        lit = ( blocklvl , skylvl , ao * FACE_SHADE[face] )
                  │          │             │
                  └── uv ────┘             └─ flat p face dim, FACE_SHADE
                       │
                       ▼
              lightmap, 16x16 rgb texture
```



## threads

```
mesh_builder_thread   (1)
    ├─ drains queue_chunkbuild
    ├─ ungen chunk: submit to gen pool, await future
    ├─ cap CHUNK_PARALLEL=32 in-flight futures
    └─ gen chunk: bake_skylight() -> build_meshjit() -> queue_meshupload

io_thread             (1)
    └─ drains save_queue -> pickle.dump

main / GL
    └─ each frame drain queue_meshupload until:
               *  CHUNK_UPLD_CAP=16 done, or
               *  CHUNK_UPLD_BUDG_L=16ms (small Q) / _H=100ms (large Q) burned
               *  -> chunk.upload_mesh()
```



> cam: first person, third back, third front, orbital (`F5`), + freecam (`Shift+F5`) with
> detach (`C`) and stick (`V`)

## network

custom proto over TCP. 
1b opcode + LE payload

**server owned world** (new) -> client now only renders on `chunker.netmode = True`
```
join ──► server keep a circle of SIM_DIST = RENDER_DIST+1 around player
           │
           ▼
         CHUNK_DATA, zlib'd voxel, ~27x, ~2.4KB/chunk
         STREAM_MAX = 24 p player p pass
```

> player identity is stored as 16 byte token in `client/token.bin`



commands (`content/commands/`) run `CommandManager` on both client and server, with
`@a @p @e @s[...]` selectors


## saves

```
saves/<world>/
  <cx>_<cz>.pkl      mods for chunk(cx,cz)
  <cx>_<cz>.ent      entity for chunk(cx,cz)
  players/           token
  cache/             NUMBA_CACHE_DIR
```


## config

```python
RENDER_DIST  = 10     # chunk radius
CHUNK_H      = 128
SEA_LEVEL    = 64
SEED         = 12345
FOV          = 70.0
SENSIVITY    = 0.15

SV_PORT      = 25250   
SV_RATE = 30   
SV_MAXONLINE = 20   
SV_PVP = True
```

> [!NOTE] 
> tested and developed on a Lenovo IdeaPad L340 (i7 9gen, GTX 1050). `RENDER_DIST > 14` saturate the builder

```python
CHUNK_WORKERS     = 8            # numba nogil workers
CHUNK_PARALLEL    = 32           # parallel gen cap
CHUNK_MESH_PTICK  = 16           # cap mesh build p/ thread iter


CHUNK_UPLD_BUDG_L = 0.016        # small Q, 16ms = 1 frame @60fps
CHUNK_UPLD_BUDG_H = 0.100        # large Q, 100ms -> fast
CHUNK_UPLD_CAP    = 16  
CHUNK_UPD_CACHE_D = 2.0          # min dist := refresh visible chunk cache

VERTEX_BUFF_POOL_SZ = 32         # prealloc buffs
VERTEX_BUFF_CAP_SZ  = 1_500_000  # float cap p vert buff
```


## license

Public domain project. feel free to change, fork and republish it, give credit.
