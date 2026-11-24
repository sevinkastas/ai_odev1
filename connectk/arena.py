"""Turnuva provası için basit hakem: iki ajan PROGRAMINI (ayrı süreç) birbirine karşı oynatır.

    python arena.py --R 7 --C 8 --K 5 --V 1 --seed 7
    python arena.py --a "python agent.py" --b "python agent.py --depth 3" --V 2

Kurallar turnuvadaki gibi: her hamle için 'MOVES ...' satırı gönderilir, cevap süresi (süreç ve G/Ç dahil)
ölçülür. Süreyi (1 s) aşan ya da yasa dışı hamle yapan ajan o oyunu kaybeder.
"""

import argparse
import queue
import shlex
import subprocess
import sys
import threading
import time

from game import Game, MAX, MIN

sys.stdout.reconfigure(encoding="utf-8")


class Player:
    """Bir ajan sürecini başlatır; stdout satırlarını ayrı bir thread ile kuyruğa okur (zaman aşımı için)."""

    def __init__(self, cmd, game_args, name):
        self.name = name
        self.proc = subprocess.Popen(shlex.split(cmd) + game_args, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, encoding="utf-8", bufsize=1)
        self.lines = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        for line in self.proc.stdout:
            self.lines.put(line.strip())

    def ask(self, moves, timeout):
        """MOVES satırını gönder, (cevap, süre) döndür. Zaman aşımında cevap None."""
        t0 = time.perf_counter()
        self.proc.stdin.write("MOVES " + " ".join(map(str, moves)) + "\n")
        self.proc.stdin.flush()
        try:
            ans = self.lines.get(timeout=timeout + 0.5)   # biraz bekle ki gerçek süre ölçülebilsin
        except queue.Empty:
            ans = None
        return ans, time.perf_counter() - t0

    def close(self):
        try:
            self.proc.stdin.write("QUIT\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=2)
        except Exception:
            self.proc.kill()


def play(game, cmd_a, cmd_b, game_args, limit=1.0, warmup=True):
    """A = MAX (ilk oyuncu), B = MIN. Döndürür: (sonuç metni, kazanan 'A'/'B'/None, hamleler, en uzun süre)."""
    players = {MAX: Player(cmd_a, game_args, "A"), MIN: Player(cmd_b, game_args, "B")}
    if warmup:
        time.sleep(1.0)            # süreçlerin import süresi ilk hamleye sayılmasın
    s = game.initial_state()
    moves, max_time = [], {"A": 0.0, "B": 0.0}
    result, winner = None, None
    try:
        while not game.is_terminal(s):
            p = players[s.to_move]
            ans, dt = p.ask(moves, limit)
            max_time[p.name] = max(max_time[p.name], dt)
            other = "B" if p.name == "A" else "A"
            if ans is None or dt > limit:
                result, winner = f"{p.name} süreyi aştı ({dt:.3f} s)", other
                break
            try:
                a = int(ans)
            except ValueError:
                result, winner = f"{p.name} geçersiz çıktı: {ans!r}", other
                break
            if a not in game.actions(s):
                result, winner = f"{p.name} yasa dışı hamle: {a}", other
                break
            moves.append(a)
            s = game.result(s, a)
        if result is None:
            w = game.winner(s)
            winner = {MAX: "A", MIN: "B"}.get(w)
            result = f"{winner} kazandı" if winner else "berabere"
    finally:
        for p in players.values():
            p.close()
    return result, winner, moves, max_time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="python agent.py")
    ap.add_argument("--b", default="python agent.py")
    ap.add_argument("--R", type=int, default=6)
    ap.add_argument("--C", type=int, default=8)
    ap.add_argument("--K", type=int, default=5)
    ap.add_argument("--V", type=int, default=2)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=float, default=1.0)
    args = ap.parse_args()
    game = Game(args.R, args.C, args.K, args.V, args.seed)
    game_args = ["--R", str(args.R), "--C", str(args.C), "--K", str(args.K),
                 "--V", str(args.V), "--seed", str(args.seed)]
    result, winner, moves, max_time = play(game, args.a, args.b, game_args, args.limit)
    s = game.from_moves(moves)
    print(game.render(s))
    print(f"Sonuç: {result} | {len(moves)} hamle | en uzun yanıt A {max_time['A']:.3f} s, "
          f"B {max_time['B']:.3f} s")
    print("Hamleler:", " ".join(map(str, moves)))


if __name__ == "__main__":
    main()
