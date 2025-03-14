def update_github_repo(csv_data):
    if not csv_data:
        print(f"[{datetime.now()}] No CSV data to commit")
        return

    print(f"[{datetime.now()}] Updating GitHub repository")

    try:
        github_token = os.environ.get("GITHUB_TOKEN")
        github_repo = os.environ.get("GITHUB_REPOSITORY")

        print(f"[{datetime.now()}] Connecting to GitHub repository: {github_repo}")

        g = Github(github_token)
        repo = g.get_repo(github_repo)

        try:
            repo.get_contents("data")
            print(f"[{datetime.now()}] Data directory exists in repo")
        except Exception as e:
            print(f"[{datetime.now()}] Data directory does not exist, creating README.md")
            repo.create_file(
                "data/README.md",
                "Create data directory",
                "# CSV Data from PriceLabs\n\nThis directory contains automatically fetched CSV data.",
                branch='main'  # ✅ Explicit branch
            )

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"data/pricelabs-{today}.csv"

        try:
            contents = repo.get_contents(filename)
            print(f"[{datetime.now()}] File {filename} exists, updating it...")
            repo.update_file(
                path=filename,
                message=f"Update CSV data from PriceLabs - {today}",
                content=csv_data,
                sha=contents.sha,
                branch='main'  # ✅ Explicit branch
            )
            print(f"[{datetime.now()}] Updated file: {filename}")
        except Exception as e:
            print(f"[{datetime.now()}] File {filename} does not exist, creating it...")
            repo.create_file(
                path=filename,
                message=f"Add CSV data from PriceLabs - {today}",
                content=csv_data,
                branch='main'  # ✅ Explicit branch
            )
            print(f"[{datetime.now()}] Created file: {filename}")

        try:
            latest = repo.get_contents("data/latest.csv")
            print(f"[{datetime.now()}] latest.csv exists, updating it...")
            repo.update_file(
                path="data/latest.csv",
                message=f"Update latest CSV data - {today}",
                content=csv_data,
                sha=latest.sha,
                branch='main'  # ✅ Explicit branch
            )
            print(f"[{datetime.now()}] Updated latest.csv")
        except Exception as e:
            print(f"[{datetime.now()}] latest.csv does not exist, creating it...")
            repo.create_file(
                path="data/latest.csv",
                message=f"Add latest CSV data - {today}",
                content=csv_data,
                branch='main'  # ✅ Explicit branch
            )
            print(f"[{datetime.now()}] Created latest.csv")

    except Exception as e:
        print(f"[{datetime.now()}] Error updating GitHub: {e}")
