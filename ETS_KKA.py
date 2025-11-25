import time
import sys
import random
import copy
import matplotlib.pyplot as plt

# Meningkatkan batas rekursi agar Naive Solver tidak crash di level sulit
sys.setrecursionlimit(20000)

# ==============================================================================
# BAGIAN 1: SUDOKU GENERATOR (DENGAN VISUALISASI)
# ==============================================================================
class SudokuGenerator:
    def __init__(self):
        self.board = [[0 for _ in range(9)] for _ in range(9)]
        self.puzzle = []
        self.solution = []

    def _is_safe(self, row, col, num):
        for x in range(9):
            if self.board[row][x] == num or self.board[x][col] == num: return False
        start_row, start_col = row - row % 3, col - col % 3
        for i in range(3):
            for j in range(3):
                if self.board[i + start_row][j + start_col] == num: return False
        return True

    def _fill_board(self):
        for i in range(9):
            for j in range(9):
                if self.board[i][j] == 0:
                    nums = list(range(1, 10))
                    random.shuffle(nums)
                    for num in nums:
                        if self._is_safe(i, j, num):
                            self.board[i][j] = num
                            if self._fill_board(): return True
                            self.board[i][j] = 0
                    return False
        return True

    def generate(self, difficulty='medium'):
        self.board = [[0 for _ in range(9)] for _ in range(9)]
        for i in range(0, 9, 3): self._fill_box(i, i)
        self._fill_board()
        self.solution = [row[:] for row in self.board]

        if difficulty == 'mudah': attempts = 30
        elif difficulty == 'sedang': attempts = 45
        else: attempts = 58 

        while attempts > 0:
            row, col = random.randint(0, 8), random.randint(0, 8)
            if self.board[row][col] != 0:
                self.board[row][col] = 0
                attempts -= 1
        
        self.puzzle = [row[:] for row in self.board]
        return self._to_string(self.board), self.puzzle, self.solution

    def _fill_box(self, row, col):
        for i in range(3):
            for j in range(3):
                while True:
                    num = random.randint(1, 9)
                    if self._is_safe_in_box(row, col, num): break
                self.board[row + i][col + j] = num

    def _is_safe_in_box(self, row_start, col_start, num):
        for i in range(3):
            for j in range(3):
                if self.board[row_start + i][col_start + j] == num: return False
        return True

    def _to_string(self, board):
        s = ""
        for row in board:
            for val in row: s += str(val)
        return s

def plot_sudoku(board, title="Sudoku Board"):
    fig, ax = plt.subplots(figsize=(6, 6))
    for i in range(10):
        lw = 2 if i % 3 == 0 else 0.5
        ax.plot([i, i], [0, 9], color='black', linewidth=lw)
        ax.plot([0, 9], [i, i], color='black', linewidth=lw)
    for i in range(9):
        for j in range(9):
            num = board[i][j]
            if num != 0: ax.text(j + 0.5, 8.5 - i, str(num), fontsize=20, ha='center', va='center')
    ax.set_xlim(0, 9); ax.set_ylim(0, 9)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=16)
    ax.spines['top'].set_visible(False); ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.show()

# ==============================================================================
# BAGIAN 2: INTELLIGENT SOLVER (DIPERBAIKI URUTAN INISIALISASINYA)
# ==============================================================================
class IntelligentSudokuSolver:
    def __init__(self, puzzle_string):
        # PERBAIKAN: Inisialisasi variable INI DULU sebelum memanggil initial_setup
        self.domains = {}
        self.peers = {}
        self.nodes_explored = 0 # <- INI HARUS DI SINI
        
        # Baru panggil initial_setup
        self.is_initialized_correctly = self.initial_setup(puzzle_string)

    def initial_setup(self, puzzle_str):
        digits = '123456789'; rows = 'ABCDEFGHI'; cols = digits
        squares = [r + c for r in rows for c in cols]
        units = {}
        for s in squares:
            r_idx, c_idx = rows.index(s[0]), cols.index(s[1])
            row_units = [rows[r_idx] + c for c in cols]
            col_units = [r + cols[c_idx] for r in rows]
            r_box = (r_idx // 3) * 3; c_box = (c_idx // 3) * 3
            box_units = [rows[r_box+i] + cols[c_box+j] for i in range(3) for j in range(3)]
            units[s] = [row_units, col_units, box_units]
            self.peers[s] = set(sum(units[s], [])) - {s}

        for s in squares: self.domains[s] = set(digits)
        for i, char in enumerate(puzzle_str):
            if char in digits:
                if not self.assign(self.domains.copy(), squares[i], char): return False
        return True

    def assign(self, domains, square, val):
        # Sekarang aman memanggil ini karena sudah di-init di __init__
        self.nodes_explored += 1 
        
        other_values = domains[square] - {val}
        if all(self.eliminate(domains, square, ov) for ov in other_values):
            return domains
        else:
            return None

    def eliminate(self, domains, square, val):
        if val not in domains[square]: return domains
        domains[square].remove(val)
        if len(domains[square]) == 0: return None
        if len(domains[square]) == 1:
            remaining_val = list(domains[square])[0]
            if not self.assign(domains, square, remaining_val): return None
        for peer in self.peers[square]:
            if not self.eliminate(domains, peer, val): return None
        return domains

    def find_mrv_cell(self, domains):
        unassigned = [(len(domains[s]), s) for s in domains if len(domains[s]) > 1]
        if not unassigned: return None
        return sorted(unassigned)[0][1]

    def solve(self):
        # Reset counter di awal proses solve
        self.nodes_explored = 0 
        
        if not self.is_initialized_correctly: return None
        
        # Lakukan inisialisasi ulang pada copy domain untuk menghitung langkah awal
        domains_copy = self.domains.copy()
        
        # Trik untuk memicu penghitungan langkah dari state awal yang sudah di-load
        # Kita iterasi semua sel yang sudah punya nilai pasti (singleton),
        # dan panggil assign untuk mereka. Ini akan menambah counter nodes_explored
        # sesuai jumlah sel yang terisi otomatis oleh constraint propagation awal.
        initial_assignments_made = False
        for s in self.domains:
             if len(self.domains[s]) == 1:
                  val = list(self.domains[s])[0]
                  # Panggil assign untuk memicu counter, tapi gunakan domain copy
                  # agar tidak merusak state utama.
                  self.assign(domains_copy, s, val)
                  initial_assignments_made = True

        # Cek apakah puzzle sudah selesai setelah inisialisasi ulang ini
        if all(len(domains_copy[s]) == 1 for s in domains_copy):
             return domains_copy # Selesai tanpa backtracking

        # Jika belum selesai, lanjut ke backtracking
        return self.backtrack(domains_copy)

    def backtrack(self, domains):
        square = self.find_mrv_cell(domains)
        if square is None: return domains
        
        for val in sorted(list(domains[square])):
            new_domains = self.assign(domains.copy(), square, val)
            if new_domains:
                result = self.backtrack(new_domains)
                if result: return result
        return None

# ==============================================================================
# BAGIAN 3: NAIVE SOLVER (BACKTRACKING BIASA)
# ==============================================================================
class NaiveSudokuSolver:
    def __init__(self, puzzle_string):
        self.board = []
        for i in range(9):
            row = [int(char) for char in puzzle_string[i*9 : (i+1)*9]]
            self.board.append(row)
        self.nodes_explored = 0

    def find_empty_linear(self):
        for i in range(9):
            for j in range(9):
                if self.board[i][j] == 0: return (i, j)
        return None

    def is_valid_now(self, row, col, num):
        for k in range(9):
            if self.board[row][k] == num: return False
            if self.board[k][col] == num: return False
        start_row, start_col = (row // 3) * 3, (col // 3) * 3
        for i in range(3):
            for j in range(3):
                if self.board[start_row + i][start_col + j] == num: return False
        return True

    def solve(self):
        self.nodes_explored = 0
        return self._backtrack_recursive()

    def _backtrack_recursive(self):
        self.nodes_explored += 1
        empty_pos = self.find_empty_linear()
        if not empty_pos: return True
        row, col = empty_pos
        for num in range(1, 10):
            if self.is_valid_now(row, col, num):
                self.board[row][col] = num
                if self._backtrack_recursive(): return True
                self.board[row][col] = 0
        return False

# ==============================================================================
# BAGIAN 4: BENCHMARKING & VISUALISASI
# ==============================================================================
def run_benchmark(solver_instance, solver_name):
    print(f"  -> Menjalankan {solver_name}...", end="\r")
    start_time = time.perf_counter()
    result = solver_instance.solve()
    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    return duration_ms, solver_instance.nodes_explored, result

def plot_results(results):
    levels = [r['Level'] for r in results]
    naive_times = [r['Naive Time Raw'] for r in results]
    int_times = [r['Int. Time Raw'] for r in results]

    x = range(len(levels)); width = 0.35
    fig, ax = plt.subplots(figsize=(10, 6))
    bar1 = ax.bar([i - width/2 for i in x], naive_times, width, label='Naive Backtracking', color='#ff9999')
    bar2 = ax.bar([i + width/2 for i in x], int_times, width, label='Intelligent (CP+MRV)', color='#66b3ff')

    ax.set_ylabel('Waktu Eksekusi (milidetik) - Log Scale')
    ax.set_title('Perbandingan Performa Sudoku Solver')
    ax.set_xticks(x); ax.set_xticklabels(levels); ax.legend()
    ax.set_yscale('log') # Skala Logaritmik

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            label = f"{height:.1f}" if height < 100000 else ">100s"
            ax.annotate(f'{label}', xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    autolabel(bar1); autolabel(bar2)
    plt.grid(axis='y', linestyle='--', alpha=0.7); plt.tight_layout()
    print("\n[INFO] Menampilkan grafik perbandingan performansi..."); plt.show()

# ==============================================================================
# BAGIAN UTAMA (MAIN)
# ==============================================================================
if __name__ == "__main__":
    generator = SudokuGenerator()
    levels = ["mudah", "sedang", "sulit"]
    results_table = []
    
    print("\n" + "="*60)
    print("   GENERATOR & BENCHMARK SUDOKU   ")
    print("="*60)
    print("PERINGATAN: Pengujian Naive Solver tingkat 'SULIT' mungkin")
    print("memakan waktu beberapa menit. Harap bersabar.")
    print("="*60)

    for level in levels:
        print(f"\n" + "="*40)
        print(f"[PENGUJIAN TINGKAT: {level.upper()}]")
        print("="*40)
        
        print(f"  [1] Generating Puzzle...")
        puzzle_str, puzzle_board, solution_board = generator.generate(level)
        print(f"      Puzzle String: {puzzle_str[:15]}...")
        print("      -> Menampilkan gambar puzzle ...")
        plot_sudoku(puzzle_board, title=f"Sudoku Puzzle (Tingkat: {level.capitalize()})")

        print(f"  [2] Menjalankan Intelligent Solver...")
        int_solver = IntelligentSudokuSolver(puzzle_str)
        t_int, n_int, res_int = run_benchmark(int_solver, "Intelligent Solver")
        print(f"      Selesai: {t_int:.2f} ms | {n_int} langkah (Assignment)")

        print(f"  [3] Menjalankan Naive Solver...")
        print("      (Proses ini mungkin lama untuk level sulit...)")
        naive_solver = NaiveSudokuSolver(puzzle_str)
        t_naive, n_naive, res_naive = run_benchmark(naive_solver, "Naive Solver")
        print(f"      Selesai: {t_naive:.2f} ms | {n_naive} langkah (Rekursi)")
        
        print("      -> Menampilkan gambar solusi ...")
        plot_sudoku(solution_board, title=f"Sudoku Solution (Tingkat: {level.capitalize()})")

        speedup = t_naive / t_int if t_int > 0 else 0
        results_table.append({
            "Level": level.capitalize(),
            "Naive Time Raw": t_naive,
            "Int. Time Raw": t_int,
            "Naive Time": f"{t_naive:.2f}",
            "Int. Time": f"{t_int:.2f}",
            "Speedup": f"{speedup:.1f}x",
            "Nodes": n_int
        })

    print("\n" + "="*85)
    print("   RINGKASAN HASIL PENGUJIAN   ")
    print("="*85)
    print(f"{'Level':<10} | {'Naive Time (ms)':<18} | {'Int. Time (ms)':<15} | {'Speedup':<10} | {'Int. Steps':<10}")
    print("-" * 85)
    for r in results_table:
        print(f"{r['Level']:<10} | {r['Naive Time']:<18} | {r['Int. Time']:<15} | {r['Speedup']:<10} | {r['Nodes']:<10}")
    print("-" * 85)
    print("Catatan: 'Int. Steps' adalah jumlah operasi assignment nilai yang berhasil.")

    plot_results(results_table)