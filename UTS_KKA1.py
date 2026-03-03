# Import library standar
import random  # Untuk mengacak urutan angka (saat membuat solusi) dan urutan sel (saat melubangi)
import copy    # Untuk 'deepcopy', membuat salinan penuh dari state papan (krusial untuk backtracking)
import sys     # Untuk mengakses sistem, khususnya menambah batas rekursi

# Solver Sudoku dengan Constraint Propagation bisa sangat dalam.
# Kita menaikkan batas rekursi Python agar program tidak crash.
sys.setrecursionlimit(2000) 

class Sudoku:
    """
    Ini adalah kelas (blueprint) untuk objek Sudoku.
    
    Program ini mengimplementasikan 3 konsep inti AI:
    1. Algoritma Backtracking: Mesin 'coba-coba' rekursif (_solve_and_find_all).
    2. Constraint Propagation (AC-3): Logika 'pintar' untuk mengurangi
       pilihan secara proaktif (_assign & _eliminate).
    3. Heuristik (MRV): Strategi 'cerdas' untuk memilih sel
       mana yang akan diisi selanjutnya (_find_mrv_cell).
    """

    def __init__(self, size=9):
        """
        Constructor. Dipanggil saat 'game = Sudoku()' dibuat.
        Mempersiapkan properti dasar.
        """
        self.size = size  # Ukuran papan (9x9)
        self.box_size = int(size**0.5)  # Ukuran kotak (3x3)
        
        # 'peers' adalah 'cache' (data simpanan) yang sangat penting.
        # Ini adalah kamus (dictionary) yang menyimpan daftar SEMUA tetangga
        # (baris, kolom, kotak) untuk setiap sel.
        # Ini dihitung sekali saja agar tidak perlu dicari berulang-ulang.
        self.peers = self._precompute_peers()
        
        # Variabel untuk menyimpan papan puzzle (integer) dan solusi (integer)
        self.board_puzzle_ints = []
        self.solution_board_ints = []

    # --- FUNGSI SETUP DAN HELPER ---
    
    def _precompute_peers(self):
        """
        Membuat 'cache' dari semua tetangga (peers) untuk setiap sel.
        Tetangga adalah sel lain di baris, kolom, atau kotak yang sama.
        Tujuan: Efisiensi. Dijalankan 1x saat inisialisasi.
        """
        peers = {} # Kamus untuk menyimpan { (r,c) : [daftar tetangga] }
        for r in range(self.size):
            for c in range(self.size):
                peer_set = set() # Gunakan 'set' untuk menghindari duplikasi
                
                # 1. Tambah tetangga di baris yang sama
                for j in range(self.size):
                    peer_set.add((r, j))
                
                # 2. Tambah tetangga di kolom yang sama
                for i in range(self.size):
                    peer_set.add((i, c))
                    
                # 3. Tambah tetangga di kotak 3x3 yang sama
                box_r_start = (r // self.box_size) * self.box_size
                box_c_start = (c // self.box_size) * self.box_size
                for i in range(box_r_start, box_r_start + self.box_size):
                    for j in range(box_c_start, box_c_start + self.box_size):
                        peer_set.add((i, j))
                
                # Hapus sel itu sendiri dari daftar tetangganya
                peer_set.remove((r, c)) 
                peers[(r, c)] = list(peer_set) # Simpan sebagai list
        return peers

    def _create_empty_domains(self):
        """
        Membuat STRUKTUR DATA INTI.
        Alih-alih papan berisi '0', kita buat papan (list 2D) di mana
        SETIAP sel berisi 'set' (himpunan) semua kemungkinan angka, yaitu {1, 2.. 9}.
        Ini disebut "Domain" dari sebuah variabel (sel).
        """
        full_domain = set(range(1, self.size + 1))
        # Buat list 2D, pastikan setiap 'set' adalah salinan unik (.copy())
        return [[full_domain.copy() for _ in range(self.size)] for _ in range(self.size)]

    def load_puzzle_into_domains(self, puzzle_ints, domains):
        """
        Jembatan antara papan 'int' (dengan 0) dan papan 'domain' (dengan set).
        Fungsi ini mengambil puzzle 'int' dan mengisinya ke 'domains'.
        
        PENTING: Saat mengisi, ia memanggil '_assign', yang memicu
        CONSTRAINT PROPAGATION awal.
        """
        for r in range(self.size):
            for c in range(self.size):
                num = puzzle_ints[r][c]
                if num != 0: # Jika sel tidak kosong
                    # Panggil '_assign'. Ini akan mengatur domain sel ini ke {num}p
                    # DAN menyebarkan (propagate) kendala ini ke tetangganya.
                    if not self._assign(domains, r, c, num):
                        # Jika _assign gagal (misal puzzle-nya 5 5 ...),
                        # berarti puzzle awal tidak valid.
                        return False 
        return True # Puzzle berhasil di-load

    def _convert_domains_to_board(self, domains):
        """
        Jembatan kembali dari 'domain' ke 'int' (untuk dicetak).
        Mengubah papan 'set' kembali menjadi papan 'int'.
        """
        board_ints = []
        for r in range(self.size):
            row = []
            for c in range(self.size):
                domain = domains[r][c]
                # Jika domain sel hanya punya 1 anggota, berarti sel itu terisi
                if len(domain) == 1:
                    row.append(list(domain)[0])
                else:
                    # Jika domain punya > 1 anggota, berarti sel itu belum terisi
                    row.append(0) 
            board_ints.append(row)
        return board_ints

    def print_board(self, board_ints):
        """Fungsi utilitas untuk mencetak papan (format int) dengan rapi."""
        print("-" * 25)
        for i in range(self.size):
            if i % self.box_size == 0 and i != 0:
                print("-" * 25) # Pemisah baris
            for j in range(self.size):
                if j % self.box_size == 0 and j != 0:
                    print("| ", end="") # Pemisah kolom
                print(f"{board_ints[i][j]} ", end="")
            print() # Baris baru
        print("-" * 25)

    # --- FUNGSI INTI (BACKTRACKING & PROPAGATION) ---
    
    def _assign(self, domains, r, c, num_to_assign):
        """
        =========================================================
        KONSEP KUNCI #1: CONSTRAINT PROPAGATION (Bagian 1 - "Bos")
        =========================================================
        Menetapkan 'num_to_assign' ke sel (r,c).
        Tugasnya:
        1. Mengatur domain (r,c) agar HANYA berisi {num_to_assign}.
        2. MENYEBARKAN (propagate) kendala ini ke semua tetangga (peers).
        """
        
        # 1. Hapus semua nilai LAIN dari sel (r,c)
        other_values = domains[r][c].copy()
        other_values.remove(num_to_assign)
        
        # Panggil _eliminate untuk setiap nilai lain.
        # Jika salah satu gagal, berarti penetapan ini tidak valid.
        for val in other_values:
            if not self._eliminate(domains, r, c, val):
                return False

        # 2. SEBARKAN (PROPAGATE) ke semua tetangga
        # Beri tahu semua tetangga (peers) bahwa mereka tidak boleh lagi
        # berisi 'num_to_assign'
        for peer_r, peer_c in self.peers[(r, c)]:
            if not self._eliminate(domains, peer_r, peer_c, num_to_assign):
                return False # Propagasi gagal (menyebabkan kontradiksi)
                
        return True # Penetapan dan propagasi berhasil

    def _eliminate(self, domains, r, c, num_to_eliminate):
        """
        =========================================================
        KONSEP KUNCI #1: CONSTRAINT PROPAGATION (Bagian 2 - "Pekerja")
        =========================================================
        Menghapus 'num_to_eliminate' dari domain sel (r,c).
        Ini adalah inti dari algoritma AC-3.
        """
        
        # Jika angka itu tidak ada di domain, tidak ada yg perlu dilakukan
        if num_to_eliminate not in domains[r][c]:
            return True 

        # Hapus angka dari domain
        domains[r][c].remove(num_to_eliminate)
        
        # --- LOGIKA 1: Cek Kontradiksi ---
        # Jika domain sel ini jadi KOSONG (len=0), berarti ada yang salah.
        # Ini adalah kontradiksi. Langkah ini gagal.
        if not domains[r][c]:
            return False # Gagal!

        # --- LOGIKA 2: Cek Propagasi Rekursif (Inti AC-3) ---
        # Jika domain sel ini jadi HANYA 1 (singleton)...
        if len(domains[r][c]) == 1:
            # ...kita dapatkan satu-satunya angka yang tersisa
            last_remaining_num = list(domains[r][c])[0]
            
            # ...maka kita harus MENYEBARKAN kendala BARU ini.
            # Beri tahu semua tetangga (peers) dari (r,c) bahwa mereka
            # sekarang tidak boleh berisi 'last_remaining_num'.
            for peer_r, peer_c in self.peers[(r, c)]:
                if not self._eliminate(domains, peer_r, peer_c, last_remaining_num):
                    return False # Propagasi rekursif ini gagal
        
        return True # Eliminasi berhasil

    def _find_mrv_cell(self, domains):
        """
        =========================================================
        KONSEP KUNCI #2: HEURISTIK (Minimum Remaining Values - MRV)
        =========================================================
        Alih-alih memilih sel kosong secara acak/urut, kita pilih
        sel yang paling "terkendala" (paling sulit).
        
        Ini adalah sel yang punya jumlah kemungkinan (domain) PALING SEDIKIT.
        (tapi lebih dari 1, karena 1 berarti sudah terisi).
        """
        min_len = float('inf') # Mulai dengan angka tak terhingga
        best_cell = None
        
        for r in range(self.size):
            for c in range(self.size):
                domain_len = len(domains[r][c])
                # Jika domain sel ini > 1 DAN lebih kecil dari min_len sejauh ini
                if domain_len > 1 and domain_len < min_len:
                    min_len = domain_len
                    best_cell = (r, c) # Simpan sebagai sel terbaik
                    
        return best_cell # Mengembalikan (r, c) dari sel terbaik, atau None

    def _solve_and_find_all(self, domains, solutions_list, limit):
        """
        =========================================================
        KONSEP KUNCI #3: ALGORITMA BACKTRACKING (Mesin Solver)
        =========================================================
        Ini adalah fungsi rekursif yang mencoba-coba mengisi papan.
        """
        
        # Optimasi: Jika kita HANYA perlu cek keunikan (limit=2)
        # dan kita sudah menemukan 2 solusi, berhenti mencari.
        if limit and len(solutions_list) >= limit:
            return

        # 1. PILIH (SELECT): Pilih sel untuk diisi
        # Kita gunakan heuristik MRV, bukan sel acak
        find = self._find_mrv_cell(domains)
        
        # BASIS REKURSI:
        # Jika 'find' adalah None, berarti tidak ada lagi sel
        # dengan domain > 1. Semua sel sudah terisi. Solusi ditemukan!
        if not find:
            # Tambahkan solusi (dalam format int) ke daftar temuan
            solutions_list.append(self._convert_domains_to_board(domains))
            return # Kembali untuk mencari solusi lain (jika ada)

        r, c = find
        
        # 2. COBA (TRY): Iterasi setiap angka yang mungkin di domain sel tsb
        domain_copy = list(domains[r][c]) 
        
        for num in domain_copy:
            
            # --- Persiapan Backtrack ---
            # Kita buat 'snapshot' (salinan penuh) dari state papan SAAT INI
            # sebelum kita mencoba 'num'.
            domains_copy = copy.deepcopy(domains)
            
            # 3. MAJU (PROPAGATE):
            # Coba tetapkan 'num' ke sel. Ini akan memicu Constraint Propagation.
            if self._assign(domains_copy, r, c, num):
                
                # 4. REKURSI:
                # Jika penetapan & propagasi berhasil, panggil diri sendiri
                # untuk mengisi sisa papan (state 'domains_copy' yang baru).
                self._solve_and_find_all(domains_copy, solutions_list, limit)
            
            # 5. MUNDUR (BACKTRACK):
            # Jika _assign gagal (langsung) ATAU jika rekursi di atas
            # kembali tanpa menemukan solusi (jalan buntu),
            # 'domains_copy' akan dibuang.
            # Loop 'for' akan lanjut ke 'num' berikutnya, menggunakan
            # 'domains' ASLI (state sebelum di-deepcopy).
            # Inilah proses "mundur" atau "mengurungkan" langkah.

    def find_all_solutions(self, puzzle_ints):
        """
        Fungsi publik (yang bisa dipanggil dari luar) untuk
        mencari SEMUA solusi.
        """
        # 1. Buat papan 'domains' kosong
        domains = self._create_empty_domains()
        
        # 2. Load puzzle (melakukan propagasi kendala awal)
        if not self.load_puzzle_into_domains(puzzle_ints, domains):
            return [] # Puzzle tidak valid
            
        # 3. Panggil solver backtracking
        solutions_list = []
        self._solve_and_find_all(domains, solutions_list, limit=None) # limit=None -> cari semua
        return solutions_list

    # --- FUNGSI GENERATOR (Diadaptasi) ---

    def _fill_solution(self, domains):
        """
        Solver yang dimodifikasi untuk membuat SATU solusi LENGKAP dan ACAK.
        Digunakan oleh generator.
        """
        find = self._find_mrv_cell(domains)
        if not find:
            return domains # Basis Rekursi: Solusi ditemukan

        r, c = find
        
        # KUNCI UTAMA GENERATOR:
        # Acak urutan angka di domain sebelum dicoba.
        domain_list = list(domains[r][c])
        random.shuffle(domain_list)
        
        for num in domain_list:
            # 'snapshot' diperlukan untuk backtracking
            domains_snapshot = copy.deepcopy(domains)
            
            # Coba tetapkan 'num' (ini memodifikasi 'domains' secara langsung)
            if self._assign(domains, r, c, num):
                # Rekursi
                solution_domains = self._fill_solution(domains)
                if solution_domains:
                    return solution_domains
            
            # Backtrack: Jika 'num' gagal, kembalikan 'domains' ke
            # state 'snapshot' sebelum mencoba 'num' berikutnya.
            domains = domains_snapshot 
        
        return None # Jalan buntu, backtrack

    def generate_puzzle(self, difficulty='medium'):
        """
        Fungsi publik untuk membuat puzzle baru
        dengan JAMINAN SATU SOLUSI UNIK.
        """
        
        print("   Langkah 1/3: Membuat solusi lengkap...")
        # 1. Buat papan domain kosong
        empty_domains = self._create_empty_domains()
        # 2. Isi menjadi solusi acak
        solved_domains = self._fill_solution(empty_domains)
        
        if solved_domains is None:
            print("ERROR: Gagal membuat solusi awal.")
            return None
            
        # 3. Simpan solusi (format int)
        self.solution_board_ints = self._convert_domains_to_board(solved_domains)
        
        # 4. Siapkan papan puzzle (awalnya = solusi penuh)
        self.board_puzzle_ints = [row[:] for row in self.solution_board_ints]
        
        # 5. Tentukan jumlah sel yg mau dihapus (dilubangi)
        difficulty_map = {'easy': 40, 'medium': 45, 'hard': 50, 'expert': 55}
        cells_to_remove = difficulty_map.get(difficulty.lower(), 45)
        
        print("   Langkah 2/3: Melubangi papan dan mengecek keunikan...")
        # Buat daftar semua 81 koordinat sel, lalu acak urutannya
        all_cells = [(r, c) for r in range(self.size) for c in range(self.size)]
        random.shuffle(all_cells)
        
        cells_removed = 0
        for r, c in all_cells:
            if cells_removed >= cells_to_remove:
                break # Sudah cukup

            # Simpan angka (jaga-jaga)
            backup = self.board_puzzle_ints[r][c]
            self.board_puzzle_ints[r][c] = 0 # Coba hapus (buat lubang)
            
            # 6. CEK KEUNIKAN (Paling penting!)
            if not self._has_unique_solution(self.board_puzzle_ints):
                # Jika setelah dihapus, solusinya jadi > 1 (tidak unik),
                # maka KEMBALIKAN angka tadi.
                self.board_puzzle_ints[r][c] = backup 
            else:
                # Jika masih unik, biarkan lubangnya.
                cells_removed += 1
                
        print("   Langkah 3/3: Selesai.")
        return self.board_puzzle_ints

    def _has_unique_solution(self, puzzle_ints):
        """
        Helper efisien untuk mengecek keunikan.
        Memanggil solver tapi dengan 'limit=2'.
        """
        domains = self._create_empty_domains()
        if not self.load_puzzle_into_domains(puzzle_ints, domains):
            return False
            
        solutions_list = []
        # Panggil solver, beri BATAS 2.
        # Jika solver menemukan 2 solusi, ia akan langsung berhenti.
        self._solve_and_find_all(domains, solutions_list, limit=2)
        
        # Kembalikan True HANYA JIKA jumlah solusinya TEPAT 1.
        return len(solutions_list) == 1

# --- Cara Penggunaan Program ---
# Blok ini hanya berjalan jika file ini dieksekusi langsung
if __name__ == "__main__":
    
    # 1. Buat objek Sudoku
    game = Sudoku()

    # 2. Tampilkan menu dan minta input
    print("Selamat Datang di Generator & Solver Sudoku!")
    print("Implementasi: Backtracking + Constraint Propagation (AC-3) + MRV")
    print("Pilih tingkat kesulitan puzzle:")
    print("1: Easy")
    print("2: Medium")
    print("3: Hard")
    print("4. Expert")
    
    # Validasi input
    choice_map = {'1': 'easy', '2': 'medium', '3': 'hard', '4': 'expert'}
    user_choice = ""
    while user_choice not in choice_map:
        user_choice = input("Masukkan pilihan (1-4): ")
    
    difficulty_level = choice_map[user_choice]
    
    # 3. Panggil Generator
    print(f"\nMembuat Puzzle Sudoku (Tingkat: {difficulty_level})...")
    puzzle = game.generate_puzzle(difficulty_level)
    
    if puzzle: # Jika generator berhasil
        print("\nPuzzle Berhasil Dibuat (0 = Kosong):")
        game.print_board(puzzle)

        # 4. Panggil Solver
        print("\nMencari SEMUA solusi untuk puzzle ini...")
        all_solutions = game.find_all_solutions(puzzle)
        
        # 5. Cetak Hasil
        print(f"Total solusi ditemukan: {len(all_solutions)}")
        
        if not all_solutions:
            print("Puzzle ini tidak memiliki solusi.")
        else:
            # Cetak semua solusi yang ditemukan
            for i, solution_board in enumerate(all_solutions):
                print(f"\n--- Menampilkan Solusi #{i + 1} ---")
                game.print_board(solution_board)
    else:
        print("Gagal membuat puzzle. Silakan coba jalankan lagi.")