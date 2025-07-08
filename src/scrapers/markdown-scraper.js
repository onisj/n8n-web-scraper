// Markdown-focused scraper with proper asset proportions
const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');
const https = require('https');
const http = require('http');
const { URL } = require('url');

async function scrapeToMarkdown(url, outputDir, options = {}) {
  const {
    downloadAssets = true,
    preserveImageSizes = true,
    includeStyles = false,
    maxWidth = 800, // Maximum width for images in markdown
    concurrency = 5 // Number of concurrent asset downloads
  } = options;

  // Create output directories
  const assetsDir = path.join(outputDir, 'assets');
  await fs.mkdir(outputDir, { recursive: true });
  if (downloadAssets) {
    await fs.mkdir(assetsDir, { recursive: true });
  }

  console.log(`Scraping ${url} to markdown...`);

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  // Track assets for downloading
  const assets = [];
  const imageDetails = new Map(); // Store original dimensions

  if (downloadAssets) {
    // Intercept requests to capture asset URLs
    await page.setRequestInterception(true);

    page.on('request', (request) => {
      const resourceType = request.resourceType();
      if (['image', 'stylesheet', 'font'].includes(resourceType)) {
        assets.push({
          url: request.url(),
          type: resourceType
        });
      }
      request.continue();
    });
  }

  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    // Extract image dimensions if preserving proportions
    if (preserveImageSizes) {
      const imageDimensions = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('img')).map(img => {
          // Get natural dimensions when available
          const width = img.naturalWidth || img.width || 0;
          const height = img.naturalHeight || img.height || 0;

          return {
            src: img.src,
            width: width,
            height: height,
            alt: img.alt || '',
            title: img.title || ''
          };
        });
      });

      // Store image details for later use
      imageDimensions.forEach(img => {
        imageDetails.set(img.src, img);
      });
    }

    // Extract content and convert to markdown
    const content = await page.evaluate(() => {
      // Find main content area
      const mainContent = document.querySelector('main') ||
        document.querySelector('article') ||
        document.querySelector('.markdown-body') ||
        document.querySelector('[role="main"]') ||
        document.body;

      // Remove unwanted elements
      const unwantedSelectors = [
        'nav', 'header', 'footer', 'aside', '.sidebar', '.navigation',
        'script', 'style', '.ads', '.advertisement', '.social-share',
        '.cookie-banner', '.popup', '.modal', '.search-box',
        '.breadcrumb', '.pagination', '.edit-page'
      ];

      unwantedSelectors.forEach(selector => {
        const elements = mainContent.querySelectorAll(selector);
        elements.forEach(el => el.remove());
      });

      return {
        title: document.title,
        content: mainContent.innerHTML,
        url: window.location.href
      };
    });

    // Convert HTML to Markdown
    const markdown = await convertHtmlToMarkdown(content.content, {
      baseUrl: url,
      imageDetails,
      assetsDir: downloadAssets ? 'assets' : null, // Relative path for markdown links
      maxWidth
    });

    // Create markdown file
    const urlObj = new URL(url);
    const filename = generateFilename(urlObj.pathname);
    const markdownPath = path.join(outputDir, `${filename}.md`);

    // Add title and metadata
    const markdownContent = [
      `# ${content.title}`,
      ``,
      `> Original URL: [${content.url}](${content.url})`,
      `> Scraped on: ${new Date().toISOString()}`,
      ``,
      markdown
    ].join('\n');

    await fs.writeFile(markdownPath, markdownContent);
    console.log(`Markdown content saved to: ${markdownPath}`);

    // Download assets if enabled
    if (downloadAssets && assets.length > 0) {
      console.log(`Found ${assets.length} assets to download`);
      await downloadAssetsInBatches(assets, assetsDir, concurrency);
    }

    await browser.close();
    return { markdownPath, assetsDir };

  } catch (error) {
    await browser.close();
    throw error;
  }
}

// Convert HTML to Markdown with proper image sizing
async function convertHtmlToMarkdown(html, options) {
  const { baseUrl, imageDetails, assetsDir, maxWidth } = options;

  // Simple HTML to Markdown conversion
  // This is a basic implementation - for production use, consider a library like turndown

  // Replace headings
  let markdown = html;
  for (let i = 6; i >= 1; i--) {
    const regex = new RegExp(`<h${i}[^>]*>(.*?)<\/h${i}>`, 'gi');
    markdown = markdown.replace(regex, (match, content) => {
      return `\n${'#'.repeat(i)} ${content.replace(/<[^>]*>/g, '')}\n`;
    });
  }

  // Replace paragraphs
  markdown = markdown.replace(/<p[^>]*>(.*?)<\/p>/gi, (match, content) => {
    return `\n${content.replace(/<[^>]*>/g, '')}\n`;
  });

  // Replace lists
  markdown = markdown.replace(/<ul[^>]*>([\s\S]*?)<\/ul>/gi, (match, content) => {
    return `\n${content}\n`;
  });

  markdown = markdown.replace(/<ol[^>]*>([\s\S]*?)<\/ol>/gi, (match, content) => {
    return `\n${content}\n`;
  });

  markdown = markdown.replace(/<li[^>]*>(.*?)<\/li>/gi, (match, content) => {
    return `- ${content.replace(/<[^>]*>/g, '')}\n`;
  });

  // Replace code blocks
  markdown = markdown.replace(/<pre[^>]*><code[^>]*class="language-([^"]+)"[^>]*>([\s\S]*?)<\/code><\/pre>/gi, (match, language, content) => {
    return `\n\`\`\`${language}\n${content.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')}\n\`\`\`\n`;
  });

  markdown = markdown.replace(/<pre[^>]*><code[^>]*>([\s\S]*?)<\/code><\/pre>/gi, (match, content) => {
    return `\n\`\`\`\n${content.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')}\n\`\`\`\n`;
  });

  // Replace inline code
  markdown = markdown.replace(/<code[^>]*>(.*?)<\/code>/gi, (match, content) => {
    return `\`${content.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')}\``;
  });

  // Replace links
  markdown = markdown.replace(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/gi, (match, href, content) => {
    try {
      // Make relative URLs absolute
      const absoluteUrl = new URL(href, baseUrl).toString();
      return `[${content.replace(/<[^>]*>/g, '')}](${absoluteUrl})`;
    } catch (e) {
      return content.replace(/<[^>]*>/g, '');
    }
  });

  // Replace images with proper sizing
  markdown = markdown.replace(/<img[^>]*src="([^"]*)"[^>]*>/gi, (match, src) => {
    try {
      // Make relative URLs absolute
      const absoluteSrc = new URL(src, baseUrl).toString();
      const imgFilename = path.basename(new URL(absoluteSrc).pathname);

      // Get image details if available
      let imgMarkdown = '';
      if (imageDetails && imageDetails.has(absoluteSrc)) {
        const img = imageDetails.get(absoluteSrc);
        const alt = img.alt || imgFilename;

        // Calculate proportional dimensions
        let width = img.width;
        let height = img.height;

        if (width > maxWidth && width > 0) {
          const ratio = maxWidth / width;
          width = maxWidth;
          height = Math.round(height * ratio);
        }

        // Use HTML img tag in markdown to preserve dimensions
        if (assetsDir) {
          // For downloaded assets
          const assetPath = `${assetsDir}/${generateAssetFilename(absoluteSrc, 'image')}`;
          imgMarkdown = `<img src="${assetPath}" alt="${alt}" width="${width}" height="${height}" />`;
        } else {
          // Use original URL
          imgMarkdown = `<img src="${absoluteSrc}" alt="${alt}" width="${width}" height="${height}" />`;
        }
      } else {
        // Fallback if no details available
        if (assetsDir) {
          const assetPath = `${assetsDir}/${generateAssetFilename(absoluteSrc, 'image')}`;
          imgMarkdown = `![${imgFilename}](${assetPath})`;
        } else {
          imgMarkdown = `![${imgFilename}](${absoluteSrc})`;
        }
      }

      return imgMarkdown;
    } catch (e) {
      return '';
    }
  });

  // Replace blockquotes
  markdown = markdown.replace(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/gi, (match, content) => {
    // Split by lines and add > to each line
    const lines = content.replace(/<[^>]*>/g, '').split('\n');
    return `\n${lines.map(line => `> ${line}`).join('\n')}\n`;
  });

  // Replace tables (simplified)
  markdown = markdown.replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (match, content) => {
    // This is a simplified table conversion - for complex tables, use a dedicated library
    let tableMarkdown = '\n';

    // Extract rows
    const rows = content.match(/<tr[^>]*>([\s\S]*?)<\/tr>/gi) || [];

    rows.forEach((row, rowIndex) => {
      const cells = row.match(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/gi) || [];

      if (cells.length > 0) {
        tableMarkdown += '| ' + cells.map(cell => {
          return cell.replace(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/i, '$1')
            .replace(/<[^>]*>/g, '')
            .trim();
        }).join(' | ') + ' |\n';

        // Add separator after header row
        if (rowIndex === 0) {
          tableMarkdown += '| ' + cells.map(() => '---').join(' | ') + ' |\n';
        }
      }
    });

    return tableMarkdown;
  });

  // Clean up line breaks and spaces
  markdown = markdown.replace(/\n{3,}/g, '\n\n');
  markdown = markdown.replace(/<br\s*\/?>/gi, '\n');

  // Remove remaining HTML tags
  markdown = markdown.replace(/<[^>]*>/g, '');

  // Decode HTML entities
  markdown = markdown.replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");

  return markdown;
}

// Generate filename from URL path
function generateFilename(urlPath) {
  // Remove leading slash and replace slashes with underscores
  let filename = urlPath.replace(/^\//g, '').replace(/\//g, '_');

  // Handle root path
  if (!filename || filename === '') {
    filename = 'index';
  }

  // Remove trailing underscore and hash fragments
  filename = filename.replace(/_$/g, '').replace(/#.*$/g, '');

  return filename;
}

// Generate unique filename for assets
function generateAssetFilename(url, type) {
  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname;
    const extension = path.extname(pathname) || getDefaultExtension(type);
    const basename = path.basename(pathname, extension);

    // Create a unique name using parts of the path and a hash of the URL
    const hash = require('crypto').createHash('md5').update(url).digest('hex').substring(0, 8);
    return `${basename || 'asset'}_${hash}${extension}`;
  } catch (e) {
    // Fallback for invalid URLs
    const hash = require('crypto').createHash('md5').update(url).digest('hex').substring(0, 8);
    return `asset_${hash}${getDefaultExtension(type)}`;
  }
}

// Get default extension based on resource type
function getDefaultExtension(type) {
  switch (type) {
    case 'image': return '.png';
    case 'stylesheet': return '.css';
    case 'font': return '.woff';
    default: return '.bin';
  }
}

// Download assets in batches to avoid overwhelming the server
async function downloadAssetsInBatches(assets, assetsDir, concurrency) {
  const uniqueAssets = [...new Map(assets.map(asset => [asset.url, asset])).values()];
  const totalAssets = uniqueAssets.length;
  let downloadedCount = 0;
  let failedCount = 0;

  console.log(`Downloading ${totalAssets} unique assets in batches of ${concurrency}...`);

  // Process assets in batches
  for (let i = 0; i < totalAssets; i += concurrency) {
    const batch = uniqueAssets.slice(i, i + concurrency);
    const promises = batch.map(asset => {
      return downloadAsset(asset.url, assetsDir)
        .then(() => {
          downloadedCount++;
          if (downloadedCount % 10 === 0 || downloadedCount === totalAssets) {
            console.log(`Downloaded ${downloadedCount}/${totalAssets} assets...`);
          }
        })
        .catch(err => {
          failedCount++;
          console.error(`Failed to download ${asset.url}: ${err.message}`);
        });
    });

    await Promise.all(promises);
  }

  console.log(`Asset download complete: ${downloadedCount} succeeded, ${failedCount} failed`);
}

// Download individual asset
async function downloadAsset(url, assetsDir) {
  try {
    const filename = generateAssetFilename(url);
    const filepath = path.join(assetsDir, filename);

    return new Promise((resolve, reject) => {
      const protocol = url.startsWith('https:') ? https : http;

      const file = require('fs').createWriteStream(filepath);

      protocol.get(url, (response) => {
        if (response.statusCode !== 200) {
          reject(new Error(`HTTP ${response.statusCode}`));
          return;
        }

        response.pipe(file);

        file.on('finish', () => {
          file.close();
          resolve(filepath);
        });

        file.on('error', (err) => {
          require('fs').unlink(filepath, () => { });
          reject(err);
        });
      }).on('error', reject);
    });
  } catch (error) {
    throw error;
  }
}

async function main() {
  // Parse command line arguments
  const args = process.argv.slice(2);
  const url = args[0] || 'https://docs.n8n.io/';
  const outputDir = args[1] || path.join(process.cwd(), 'data', 'scraped_docs');

  // Parse options
  const options = {
    downloadAssets: !args.includes('--no-assets'),
    preserveImageSizes: !args.includes('--no-preserve-sizes'),
    maxWidth: args.includes('--max-width') ?
      parseInt(args[args.indexOf('--max-width') + 1], 10) : 800
  };

  console.log('=== Markdown Scraper ===');
  console.log(`URL: ${url}`);
  console.log(`Output Directory: ${outputDir}`);
  console.log(`Options: ${JSON.stringify(options, null, 2)}`);

  try {
    const result = await scrapeToMarkdown(url, outputDir, options);
    console.log('\n✓ Scraping completed successfully!');
    console.log(`Markdown file: ${result.markdownPath}`);
    if (options.downloadAssets) {
      console.log(`Assets directory: ${result.assetsDir}`);
    }
  } catch (error) {
    console.error('\n✗ Scraping failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { scrapeToMarkdown };