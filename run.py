from app import create_app

app = create_app()

if __name__ == '__main__':
    print("\n  GR Asset Management System")
    print("  ─────────────────────────────")
    print("  Running at: http://127.0.0.1:5000")
    print("  Network:    http://0.0.0.0:5000")
    print("  Accounts:   admin/admin123  finance/finance123  john/user123")
    print("  Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
