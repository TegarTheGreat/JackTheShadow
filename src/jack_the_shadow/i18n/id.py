"""
Jack The Shadow — Indonesian String Table (Bahasa Indonesia)

Casual hacker slang — gaya gaul Jakarta / internet Indonesia.
"""

STRINGS: dict[str, str] = {
    # ── Banner & startup
    "banner.target": "Target",
    "banner.model": "Model",
    "banner.yolo": "YOLO",
    "banner.lang": "Bahasa",
    "banner.no_target": "Belum di-set — pake /target atau bilang aja ke Jack",
    "banner.hint": "Ketik [bold]/[/bold] untuk perintah, langsung ketik untuk chat sama Jack.",
    "banner.tagline": "« Agen Cybersecurity Otonom »",
    "banner.no_creds": (
        "[warning]⚠  Belum konek ke Cloudflare AI.[/]\n"
        "[dim]  Pake [bold]/login[/bold] untuk koneksi akun Cloudflare.\n"
        "  Tool tetep jalan, tapi Jack gak bisa mikir tanpa AI backend.[/]"
    ),

    # ── Auth gate (startup)
    "auth.gate_header": "🔐 Pertama-tama — lo harus konek AI backend dulu.",
    "auth.gate_body": (
        "Jack butuh kredensial Cloudflare Workers AI buat mikir.\n"
        "  Ambil di: https://dash.cloudflare.com → AI → Workers AI"
    ),
    "auth.skipped": "Gak papa, jalan di mode offline. Pake /login kapan aja buat konek.",
    "auth.connected": "🟢 Terkoneksi ke Cloudflare Workers AI",

    # ── Welcome message
    "welcome.message": (
        "  [bold cyan]Mau ngapain nih?[/]\n"
        "  [dim]Kasih target, jelasin tantangan CTF, tanya soal CVE,\n"
        "  atau bilang aja apa yang dibutuhin. Pake /target buat lock scope.[/]"
    ),

    # ── Spinner / status
    "spinner.thinking": "Jack lagi mikir keras...",
    "spinner.tool_result": "Jack lagi proses hasil tool...",

    # ── Respons AI
    "ai.empty_response": "(Jack tidak memberikan respons.)",

    # ── YOLO mode
    "yolo.on_title": "☠  ZONA BAHAYA",
    "yolo.on_body": (
        "[warning]⚡ YOLO MODE AKTIF ⚡[/]\n"
        "Semua eksekusi tool langsung di-approve. Tanpa pengaman.\n"
        "Ketik /yolo lagi kalo udah sadar."
    ),
    "yolo.off_title": "✓ Mode Aman",
    "yolo.off_body": (
        "[green]YOLO mode dinonaktifin.[/]\n"
        "Balik ke approval manual. Langkah bijak."
    ),
    "yolo.auto_approve": "  ⚡ [YOLO MODE] Auto-approve...",

    # ── HITL approval
    "hitl.header": "⚠  PERLU PERSETUJUAN",
    "hitl.risk": "RISIKO",
    "hitl.wants_to_run": "Jack mau jalanin",
    "hitl.prompt": "  Izinin Jack jalanin ini? [Y/n]: ",
    "hitl.prompt_title": "Izinin eksekusi?",
    "hitl.cancelled": "  Dibatalin sama operator.",

    # ── Slash commands
    "cmd.yolo.desc": "Toggle mode YOLO auto-approve",
    "cmd.clear.desc": "Bersihkan konteks percakapan / memori",
    "cmd.help.desc": "Tampilkan perintah yang tersedia",
    "cmd.exit.desc": "Keluar dari Jack The Shadow",
    "cmd.model.desc": "Ganti model AI",
    "cmd.lang.desc": "Ganti bahasa (en/id)",
    "cmd.target.desc": "Set atau ubah target scope",
    "cmd.context.desc": "Tampilkan pemakaian context window",
    "cmd.tools.desc": "Daftar tool yang tersedia",
    "cmd.models.desc": "Daftar model AI yang tersedia",
    "cmd.compact.desc": "Kompres konteks (simpan N pesan terakhir)",
    "cmd.history.desc": "Daftar & lanjutkan sesi tersimpan",
    "cmd.export.desc": "Export percakapan jadi laporan markdown",
    "cmd.doctor.desc": "Cek ketersediaan tools pentesting",
    "cmd.cost.desc": "Tampilkan statistik penggunaan API",
    "cmd.memory.desc": "Lihat memori persisten / temuan",
    "cmd.plan.desc": "Lihat rencana serangan / daftar tugas",
    "cmd.permissions.desc": "Kelola aturan auto-approve",

    # ── Login / Logout
    "cmd.login.desc": "Koneksi kredensial Cloudflare AI",
    "cmd.logout.desc": "Putus koneksi / hapus kredensial tersimpan",
    "login.already_logged_in": "Lo udah login.",
    "login.source": "Kredensial dimuat dari: {source}",
    "login.overwrite_prompt": "Timpa kredensial yang ada? [y/N]: ",
    "login.instruction": "Masukin kredensial Cloudflare Workers AI lo.",
    "login.empty_fields": "Account ID dan API Token gak boleh kosong.",
    "login.success": "Kredensial disimpan di ~/.jshadow/credentials.json",
    "login.reconnect_hint": "Jack bakal auto-reconnect — gak perlu restart.",
    "logout.success": "Kredensial dihapus. Lo udah logout.",
    "logout.not_logged_in": "Gak ada kredensial tersimpan.",

    # ── Context
    "context.title": "Context Window",
    "context.messages": "Pesan",
    "context.limit": "Batas",

    # ── Tool output
    "tool.call": "Panggil tool",
    "tool.denied": "Operator menolak eksekusi.",
    "tool.timeout": "Perintah timeout setelah {timeout} detik",
    "tool.max_rounds": "Jack kena limit tool-call ({limit} ronde). Putus loop.",

    # ── Goodbye
    "goodbye": "👋 Jack menghilang ke dalam bayangan...",

    # ── Offline hint (ditampilkan saat user ngetik tapi AI belum konek)
    "offline.hint": (
        "Otak Jack belum terkoneksi. Pake [bold]/login[/bold] untuk konek "
        "Cloudflare Workers AI, atau set env vars."
    ),

    # ── Language switch
    "lang.switched": "Bahasa diganti ke Bahasa Indonesia.",
    "lang.invalid": "Bahasa nggak valid. Pakai: /lang en  atau  /lang id",

    # ── Model switch
    "model.switched": "Model diganti ke: {model}",
    "model.invalid": "Model nggak dikenal. Pakai /models untuk lihat pilihan.",

    # ── Target
    "target.switched": "Target diubah ke: {target}",
    "target.usage": "Cara pakai: /target <target_baru>",

    # ── MCP
    "cmd.mcp.desc": "Kelola koneksi MCP server",
    "mcp.title": "MCP Server",
    "mcp.no_servers": "Belum ada MCP server. Pakai: /mcp add <nama> <command> [args...]",
    "mcp.added": "MCP server '{name}' terkoneksi — {tools} tool ditemukan.",
    "mcp.add_failed": "Gagal memulai MCP server '{name}'.",
    "mcp.removed": "MCP server '{name}' terputus.",
    "mcp.usage": "Pakai: /mcp add <nama> <command> [args...] | /mcp remove <nama> | /mcp list",
}
