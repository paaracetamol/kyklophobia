import argparse
import signal
import sys
import os
import shutil
import hashlib
import time
import logformat

SDIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SDIR)
CDIR = os.path.join(ROOT, "content")



# numba cache
STAMPF = ("config.py", "world/blocks.py", "world/renderers/registry.py")

def cachestamp(cdir):
    h = hashlib.md5()
    for f in STAMPF:
        with open(os.path.join(cdir, f), "rb") as fp: h.update(fp.read())

    return h.hexdigest()

# world cache
def seedcache(cdir, content):
    st = cachestamp(content)
    sf = os.path.join(cdir, "STAMP")
    rd = lambda f: open(f).read() if os.path.exists(f) else ""

    if os.listdir(cdir) and rd(sf) != st:
        shutil.rmtree(cdir)
        os.makedirs(cdir)

    if not os.listdir(cdir):
        sv = os.path.dirname(os.path.dirname(cdir))
        cs = [os.path.join(sv, d, "cache") for d in os.listdir(sv)]
        cs = [c for c in cs if c != cdir and rd(os.path.join(c, "STAMP")) == st]
        if cs: shutil.copytree(max(cs, key=os.path.getmtime), cdir, dirs_exist_ok=True)
        
    with open(sf, "w") as fp: fp.write(st)


def _setup_path():
    os.chdir(SDIR)
    for p in (SDIR, CDIR):
        if p not in sys.path:
            sys.path.insert(0, p)





def argparser():
    from config import SV_PORT, SV_HOST, SEED, SV_MAXONLINE, SV_MOTD
    p = argparse.ArgumentParser(description="Kyklophobia Dedicated Server")
    p.add_argument("--host",                  default=SV_HOST)
    p.add_argument("--port",        type=int, default=SV_PORT)
    p.add_argument("--world",                 default="default")
    p.add_argument("--seed",        type=int, default=SEED)
    p.add_argument("--type",        default="default", choices=("default", "flat"), dest="wtype")
    p.add_argument("--max-players", type=int, default=SV_MAXONLINE, dest="maxp")
    p.add_argument("--motd",                  default=SV_MOTD)
    return p.parse_args()






def banner(args):
    print("""
⠀⢠⣏⡏⢹⡏⠉⠉⡟⠉⠉⣿⠉⠉⣽⣉⠉⢹⡏⠉⢹⡏⠉⠉⡇⠀⢸⠉⠉⠉⠉⠉⢹⡏⠉⠉⠉⠉⠉⣿⠉⠉⣿⠉⠉⢹⡉⠉⢹⠉⠉⢹⡏⠉⠉⠉⠉⠉⣿⠉⠉⢻⡉⠉⠉⠉⠉⠹⡆⠀
⠀⡾⠀⠒⠚⢁⣀⣸⠗⠂⠀⠃⠀⠀⣿⠘⠒⠛⢀⣀⣸⠇⠀⢰⣿⠀⢸⠀⠀⢸⠀⠀⢸⡇⠀⠈⠇⠀⠀⣿⠀⠀⠿⠀⠀⢸⡇⠀⠘⡇⠀⠀⣧⠀⠀⠿⠒⢂⣹⡆⠀⢸⡇⠀⠀⠧⠀⠀⢧⠀
⢠⡇⠀⠀⠀⠀⠀⣿⣿⡇⠀⠀⣿⣿⡇⠀⠀⠀⠀⠀⣸⠀⠀⢸⡿⠀⣼⠀⠀⣸⣀⣀⣸⡇⠀⠀⣤⣤⣤⣿⠀⠀⢠⡄⠀⢸⡇⠀⠀⣷⣀⣀⣻⠀⠀⢠⡄⠀⠘⡇⠀⠀⣿⠀⠀⢠⡄⠀⢸⡄
⣼⠀⠀⢸⠇⠀⢰⣿⣿⠃⢀⢰⣿⣿⠃⠀⢠⡇⠀⠀⣿⠀⠀⠈⠉⠉⡧⠄⠀⠉⠀⠀⢸⡇⡆⠀⣿⣿⣿⣿⠀⠀⢸⡇⠀⢸⣧⠄⠀⠉⠀⠀⢸⡆⠈⠈⠁⠀⠀⣿⠀⡀⢸⡄⠀⠘⡇⠀⠀⣇
⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏
⠀⠈⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠁ D E D I C A T E D  ●  S E R V E R ⠈⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠁⠀⠀⠀
    """)
    print(f"  Host:        {args.host}")
    print(f"  Port:        {args.port}")
    print(f"  World:       {args.world}")
    print(f"  Seed:        {args.seed}")
    print(f"  Type:        {args.wtype}")
    print(f"  Max Online:  {args.maxp}")
    print(f"  Directory:   saves/{args.world}/")
    print("\n")
    #exit()





def console(server):
    print("Type 'help' for available commands.\n")
    

    while server.running:
        try: line = input("").strip()
        except (EOFError, KeyboardInterrupt): break
        if not line: continue

        cmd, _, arg = line.partition(" ")
        cmd = cmd.lower()
        arg = arg.strip()

        if cmd == "help":
            print("  help   list   say <msg>   kick <name> [reason]")
            print("  seed   status   save   stop")

        elif cmd == "list":
            pl = server.pllist()
            if pl:
                print(f"Online ({len(pl)}/{server.maxpl}):")
                for pid, nm, pos in pl:
                    print(f"  [{pid}] {nm} at ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})")
                    
            else:
                print("No players online.")

        elif cmd == "say":
            if arg: server.bcastmsg(f"[Server] {arg}")
            else:   print("Usage: say <message>")

        elif cmd == "kick":
            if not arg: print("Usage: kick <name> [reason]"); continue
            nm, _, reason = arg.partition(" ")
            reason = reason or "Kicked by server"
            if server.kick(nm, reason): print(f"Kicked {nm}")
            else: print(f"Player '{nm}' not found")
            
            
            

        elif cmd == "seed":
            print(f"World seed: {server.seed}")
            
            

        elif cmd == "status":
            n  = server.pcount()
            up = time.time() - server.start_time
            h, m, s = int(up // 3600), int(up % 3600 // 60), int(up % 60)
            print(f"  Players: {n}/{server.maxpl}")
            print(f"  World:   {server.wname} (seed: {server.seed}, type: {server.wtype})")
            print(f"  Uptime:  {h:02d}:{m:02d}:{s:02d}")
            
            

        elif cmd == "save":
            if server.chunker:
                for cx, cz in list(server.chunker.dirtychunks):
                    server.chunker.save_mods(cx, cz)
                print("World saved.")
                

        elif cmd in ("stop", "quit", "exit"):
            break

        else:
            print(f"Unknown command: '{cmd}'. Type 'help'.")
            
            
            
            

    server.stop()


def main():
    logformat.setup()
    _setup_path()

    args = argparser()

    import config
    config.root = os.path.join(SDIR, "saves")
    sdir = os.path.join(config.root, args.world)
    os.makedirs(sdir, exist_ok=True)
    args.seed, args.wtype = config.worldmeta(args.world, args.seed, args.wtype)
    banner(args)

    cdir = os.path.join(sdir, "cache")
    os.makedirs(cdir, exist_ok=True)
    seedcache(cdir, os.path.join(os.path.dirname(SDIR), "content"))
    os.environ["NUMBA_CACHE_DIR"] = cdir

    from instance import Instance
    server = Instance(
        host=args.host,   port=args.port,
        wname=args.world, seed=args.seed,
        maxp=args.maxp,   motd=args.motd,
    )

    def _shutdown(sig, frame):
        print("Received shutdown signal...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    server.start()
    console(server)


if __name__ == "__main__":
    main()
