name: Update Etsy Reviews RSS

on:
  schedule:
    - cron: "0 0 * * *"   # runs daily at 00:00 UTC (change if you prefer)
  workflow_dispatch: {}   # allows manual run from GitHub UI

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4
        with:
          persist-credentials: true

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.x"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run RSS script
        run: python yoola_reviews_rss.py

      - name: Commit and push changes (if any)
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/yoola_reviews.xml || true
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "Update Yoola reviews RSS"
            git push
          fi
