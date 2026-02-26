# Prismic Image Alt Text Checker

A Python script to identify all images in Prismic documents and export them to a CSV report with their alt text status.

## Features

- Fetches all documents from a Prismic repository
- Recursively scans all fields for images
- Exports ALL images found (not just those missing alt text)
- Exports detailed CSV report with:
  - Document type
  - Document title/name
  - Document UID and ID
  - **Prismic edit URL** (direct link to edit the page)
  - Field path where the image is located
  - Image URL
  - **Alt text** (blank if missing)
  - Image dimensions
  - Last publication date
- Provides summary statistics showing images with and without alt text
- Supports both public and private repositories
- Handles pagination automatically

## Requirements

- Python 3.6+
- requests library

## Installation

```bash
pip install -r requirements.txt
```

## Usage

The script accepts the repository in multiple formats:
- Just the name: `eisejewels`
- With domain: `eisejewels.prismic.io`
- Full URL: `https://eisejewels.prismic.io`

### Basic Usage (Public Repository)

```bash
# Any of these formats work:
python find_missing_alt_text.py eisejewels
python find_missing_alt_text.py eisejewels.prismic.io
python find_missing_alt_text.py https://eisejewels.prismic.io
```

### Private Repository with Access Token

Option 1: Pass token as argument
```bash
python find_missing_alt_text.py eisejewels --token YOUR_ACCESS_TOKEN
```

Option 2: Use environment variable
```bash
export PRISMIC_ACCESS_TOKEN=your_token
python find_missing_alt_text.py your-repo-name
```

### Custom Output File

```bash
python find_missing_alt_text.py your-repo-name -o my_report.csv
```

### Get Help

```bash
python find_missing_alt_text.py --help
```

## Finding Your Repository Name

Your repository name is the subdomain of your Prismic URL. The script accepts any of these formats:
- If your Prismic URL is `https://eisejewels.prismic.io`
- You can use: `eisejewels` OR `eisejewels.prismic.io` OR `https://eisejewels.prismic.io`

## Finding Your Access Token

For private repositories:
1. Log in to your Prismic repository
2. Go to Settings → API & Security
3. Copy your Permanent access token or create a new one

## Output Format

The script generates a CSV file with the following columns:

| Column | Description |
|--------|-------------|
| document_type | The custom type of the document (e.g., page, blog_post) |
| document_title | The title or name of the document |
| document_uid | The unique identifier/slug of the document |
| document_id | The Prismic document ID |
| **prismic_url** | Direct link to edit the document in Prismic |
| field_path | The path to the image field in the document structure |
| image_url | The URL of the image |
| **alt_text** | The alt text for the image (blank if missing) |
| image_dimensions | Width x Height of the image |
| last_publication_date | When the document was last published |

## Example Output

```csv
document_type,document_title,document_uid,document_id,prismic_url,field_path,image_url,alt_text,image_dimensions,last_publication_date
page,About Us,about-us,YXZ123,https://eisejewels.prismic.io/builder/pages/YXZ123,data.hero_image,https://images.prismic.io/...,,1920x1080,2026-02-15T10:30:00+0000
blog_post,New Product Launch,new-product-launch,ABC456,https://eisejewels.prismic.io/builder/pages/ABC456,data.body[0].primary.image,https://images.prismic.io/...,Product showcase image,800x600,2026-02-20T14:45:00+0000
page,Contact,contact,DEF789,https://eisejewels.prismic.io/builder/pages/DEF789,data.banner,https://images.prismic.io/...,Contact us banner,1200x400,2026-02-22T09:15:00+0000
```

Note: 
- Images without alt text will have a blank value in the `alt_text` column (see first row above)
- Click the `prismic_url` to directly edit that document in Prismic

## Notes

- The script searches for images hosted on `images.prismic.io`
- It checks all nested fields and slices in the document structure
- The `field_path` column helps you locate exactly where in the document the image appears
- For documents without a specific title field, it will try to use the UID or document ID
- **All images are exported**, not just those missing alt text
- You can filter the CSV in Excel/Sheets for blank `alt_text` values to find images that need attention
- The summary shows statistics for images with and without alt text

## Troubleshooting

### "No master ref found"
- Check that your repository name is correct
- Verify your network connection

### "401 Unauthorized"
- Your repository might be private - add an access token
- Check that your access token is valid

### "No documents found"
- Verify the repository name is correct
- Check if the repository has published content

## License

MIT
