// Full site markdown scraper for https://docs.n8n.io/
const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');
const https = require('https');
const http = require('http');
const { URL } = require('url');
const { scrapeToMarkdown } = require('./markdown-scraper');

class FullSiteMarkdownScraper {
  constructor(baseUrl, outputDir, options = {}) {
    this.baseUrl = baseUrl;
    this.outputDir = outputDir;
    this.visitedUrls = new Set();
    this.urlQueue = [];
    this.scrapedCount = 0;
    this.errorCount = 0;
    this.maxConcurrency = options.maxConcurrency || 2; // Lower concurrency for markdown conversion
    this.delay = options.delay || 2000; // Longer delay between requests
    this.maxPages = options.maxPages || 500;
    this.downloadAssets = options.downloadAssets !== false;
    this.preserveImageSizes = options.preserveImageSizes !== false;
    this.maxImageWidth = options.maxImageWidth || 800;
    this.sharedAssetsDir = path.join(outputDir, 'shared_assets');
    this.downloadedAssets = new Map(); // Track downloaded assets to avoid duplicates
  }

  // Normalize URL for consistent comparison
  normalizeUrl(url) {
    try {
      const urlObj = new URL(url, this.baseUrl);
      // Remove hash fragments and trailing slashes
      urlObj.hash = '';
      let pathname = urlObj.pathname;
      if (pathname.endsWith('/') && pathname.length > 1) {
        pathname = pathname.slice(0, -1);
      }
      urlObj.pathname = pathname;
      return urlObj.toString();
    } catch (error) {
      return null;
    }
  }

  // Check if URL should be scraped
  shouldScrapeUrl(url) {
    try {
      const urlObj = new URL(url);
      const baseUrlObj = new URL(this.baseUrl);

      // Only scrape URLs from the same domain
      if (urlObj.hostname !== baseUrlObj.hostname) {
        return false;
      }

      // Skip certain file types and paths
      const skipPatterns = [
        /\.(pdf|jpg|jpeg|png|gif|svg|css|js|ico|woff|woff2|ttf)$/i,
        /\/api\//,
        /\/search/,
        /\/_/,
        /#/
      ];

      return !skipPatterns.some(pattern => pattern.test(url));
    } catch (error) {
      return false;
    }
  }

  // Generate directory structure from URL
  generateOutputPath(url) {
    try {
      const urlObj = new URL(url);
      let pathname = urlObj.pathname;

      // Remove leading slash
      pathname = pathname.replace(/^\//, '');

      // Handle root path
      if (!pathname || pathname === '') {
        return path.join(this.outputDir, 'index.md');
      }

      // Split path into segments
      const segments = pathname.split('/');
      const filename = segments.pop() || 'index';

      // Create directory structure
      const dirPath = segments.length > 0 ?
        path.join(this.outputDir, ...segments) :
        this.outputDir;

      return path.join(dirPath, `${filename}.md`);
    } catch (error) {
      return path.join(this.outputDir, `page_${Date.now()}.md`);
    }
  }

  // Discover URLs from a page
  async discoverUrls(page) {
    return await page.evaluate((baseUrl) => {
      const links = Array.from(document.querySelectorAll('a[href]'));
      const urls = links
        .map(link => {
          try {
            return new URL(link.href, baseUrl).toString();
          } catch (error) {
            return null;
          }
        })
        .filter(url => url !== null);

      return [...new Set(urls)]; // Remove duplicates
    }, this.baseUrl);
  }

  // Convert HTML to Markdown with shared assets
  async convertHtmlToMarkdown(html, options) {
    const { baseUrl, imageDetails, maxWidth } = options;

    // Simple HTML to Markdown conversion
    let markdown = html;

    // Replace headings
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

    // Replace images with proper sizing and shared assets
    markdown = markdown.replace(/<img[^>]*src="([^"]*)"[^>]*>/gi, (match, src) => {
      try {
        // Make relative URLs absolute
        const absoluteSrc = new URL(src, baseUrl).toString();

        // Skip data URLs (inline SVGs)
        if (absoluteSrc.startsWith('data:')) {
          return '';
        }

        const imgFilename = this.generateAssetFilename(absoluteSrc, 'image');

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

          // Use relative path to shared assets
          const relativePath = path.relative(path.dirname(options.outputPath), path.join(this.sharedAssetsDir, imgFilename));
          imgMarkdown = `<img src="${relativePath}" alt="${alt}" width="${width}" height="${height}" />`;
        } else {
          // Fallback if no details available
          const relativePath = path.relative(path.dirname(options.outputPath), path.join(this.sharedAssetsDir, imgFilename));
          imgMarkdown = `![${imgFilename}](${relativePath})`;
        }

        return imgMarkdown;
      } catch (e) {
        return '';
      }
    });

    // Replace blockquotes
    markdown = markdown.replace(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/gi, (match, content) => {
      const lines = content.replace(/<[^>]*>/g, '').split('\n');
      return `\n${lines.map(line => `> ${line}`).join('\n')}\n`;
    });

    // Replace tables (simplified)
    markdown = markdown.replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (match, content) => {
      let tableMarkdown = '\n';

      const rows = content.match(/<tr[^>]*>([\s\S]*?)<\/tr>/gi) || [];

      rows.forEach((row, rowIndex) => {
        const cells = row.match(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/gi) || [];

        if (cells.length > 0) {
          tableMarkdown += '| ' + cells.map(cell => {
            return cell.replace(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/i, '$1')
              .replace(/<[^>]*>/g, '')
              .trim();
          }).join(' | ') + ' |\n';

          if (rowIndex === 0) {
            tableMarkdown += '| ' + cells.map(() => '---').join(' | ') + ' |\n';
          }
        }
      });

      return tableMarkdown;
    });

    // Clean up
    markdown = markdown.replace(/\n{3,}/g, '\n\n');
    markdown = markdown.replace(/<br\s*\/?>/gi, '\n');
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

  // Generate unique filename for assets
  generateAssetFilename(url, type) {
    try {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname;
      const extension = path.extname(pathname) || this.getDefaultExtension(type);
      const basename = path.basename(pathname, extension);

      const hash = require('crypto').createHash('md5').update(url).digest('hex').substring(0, 8);
      return `${basename || 'asset'}_${hash}${extension}`;
    } catch (e) {
      const hash = require('crypto').createHash('md5').update(url).digest('hex').substring(0, 8);
      return `asset_${hash}${this.getDefaultExtension(type)}`;
    }
  }

  // Get default extension based on resource type
  getDefaultExtension(type) {
    switch (type) {
      case 'image': return '.png';
      case 'stylesheet': return '.css';
      case 'font': return '.woff';
      default: return '.bin';
    }
  }

  // Download asset if not already downloaded
  async downloadAssetIfNeeded(url) {
    if (this.downloadedAssets.has(url)) {
      return this.downloadedAssets.get(url);
    }

    try {
      const filename = this.generateAssetFilename(url, 'image');
      const filepath = path.join(this.sharedAssetsDir, filename);

      await this.downloadAsset(url, filepath);
      this.downloadedAssets.set(url, filepath);
      return filepath;
    } catch (error) {
      console.error(`Failed to download ${url}: ${error.message}`);
      return null;
    }
  }

  // Download individual asset
  async downloadAsset(url, filepath) {
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
  }

  // Scrape a single page to markdown
  async scrapePage(url, browser) {
    const page = await browser.newPage();

    try {
      console.log(`Scraping: ${url}`);

      // Set user agent and viewport
      await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
      await page.setViewport({ width: 1200, height: 800 });

      // Track assets
      const assets = [];
      const imageDetails = new Map();

      if (this.downloadAssets) {
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

      // Navigate to page
      await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Extract image dimensions if preserving proportions
      if (this.preserveImageSizes) {
        const imageDimensions = await page.evaluate(() => {
          return Array.from(document.querySelectorAll('img')).map(img => {
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

        imageDimensions.forEach(img => {
          imageDetails.set(img.src, img);
        });
      }

      // Extract content
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

      // Discover new URLs
      const discoveredUrls = await this.discoverUrls(page);

      // Add new URLs to queue
      for (const discoveredUrl of discoveredUrls) {
        const normalizedUrl = this.normalizeUrl(discoveredUrl);
        if (normalizedUrl &&
          !this.visitedUrls.has(normalizedUrl) &&
          this.shouldScrapeUrl(normalizedUrl) &&
          this.urlQueue.length + this.visitedUrls.size < this.maxPages) {
          this.urlQueue.push(normalizedUrl);
        }
      }

      // Generate output path
      const outputPath = this.generateOutputPath(url);

      // Ensure directory exists
      await fs.mkdir(path.dirname(outputPath), { recursive: true });

      // Convert to markdown
      const markdown = await this.convertHtmlToMarkdown(content.content, {
        baseUrl: url,
        imageDetails,
        maxWidth: this.maxImageWidth,
        outputPath
      });

      // Create markdown content with metadata
      const markdownContent = [
        `# ${content.title}`,
        ``,
        `> Original URL: [${content.url}](${content.url})`,
        `> Scraped on: ${new Date().toISOString()}`,
        ``,
        markdown
      ].join('\n');

      // Save markdown file
      await fs.writeFile(outputPath, markdownContent);

      // Download assets to shared directory
      if (this.downloadAssets && assets.length > 0) {
        const imageAssets = assets.filter(asset => asset.type === 'image');
        for (const asset of imageAssets) {
          if (!asset.url.startsWith('data:')) {
            await this.downloadAssetIfNeeded(asset.url);
          }
        }
      }

      this.scrapedCount++;
      console.log(`✓ Scraped: ${url} -> ${path.relative(this.outputDir, outputPath)} (${this.scrapedCount} total)`);

      return { outputPath, content };

    } catch (error) {
      this.errorCount++;
      console.error(`✗ Error scraping ${url}:`, error.message);
      return null;
    } finally {
      await page.close();
    }
  }

  // Main scraping function
  async scrapeFullSite() {
    console.log(`Starting full site markdown scrape of: ${this.baseUrl}`);
    console.log(`Output directory: ${this.outputDir}`);
    console.log(`Shared assets directory: ${this.sharedAssetsDir}`);

    // Ensure output directories exist
    await fs.mkdir(this.outputDir, { recursive: true });
    if (this.downloadAssets) {
      await fs.mkdir(this.sharedAssetsDir, { recursive: true });
    }

    // Initialize with base URL
    this.urlQueue.push(this.normalizeUrl(this.baseUrl));

    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
      const startTime = Date.now();

      while (this.urlQueue.length > 0 && this.visitedUrls.size < this.maxPages) {
        // Get next batch of URLs
        const batch = this.urlQueue.splice(0, this.maxConcurrency);

        // Mark URLs as visited
        batch.forEach(url => this.visitedUrls.add(url));

        // Process batch concurrently
        const promises = batch.map(url => this.scrapePage(url, browser));
        await Promise.allSettled(promises);

        // Progress update
        console.log(`Progress: ${this.visitedUrls.size} pages visited, ${this.urlQueue.length} in queue`);

        // Add delay between batches
        if (this.urlQueue.length > 0) {
          await new Promise(resolve => setTimeout(resolve, this.delay));
        }
      }

      const endTime = Date.now();
      const duration = Math.round((endTime - startTime) / 1000);

      console.log('\n=== Scraping Summary ===');
      console.log(`Total pages scraped: ${this.scrapedCount}`);
      console.log(`Total errors: ${this.errorCount}`);
      console.log(`Total assets downloaded: ${this.downloadedAssets.size}`);
      console.log(`Duration: ${duration} seconds`);
      console.log(`Output directory: ${this.outputDir}`);
      if (this.downloadAssets) {
        console.log(`Shared assets directory: ${this.sharedAssetsDir}`);
      }

      // Create index file
      await this.createIndexFile();

    } finally {
      await browser.close();
    }
  }

  // Create an index file listing all scraped pages
  async createIndexFile() {
    const indexPath = path.join(this.outputDir, 'README.md');

    const indexContent = [
      `# n8n Documentation - Scraped Content`,
      ``,
      `> Scraped from: [${this.baseUrl}](${this.baseUrl})`,
      `> Scraped on: ${new Date().toISOString()}`,
      `> Total pages: ${this.scrapedCount}`,
      `> Total assets: ${this.downloadedAssets.size}`,
      ``,
      `## Structure`,
      ``,
      `This directory contains the complete n8n documentation converted to Markdown format.`,
      ``,
      `- **Markdown files**: Each page from the documentation site`,
      `- **shared_assets/**: Images and other assets used across pages`,
      ``,
      `## Features`,
      ``,
      `- ✅ Preserved image proportions and sizing`,
      `- ✅ Clean markdown formatting`,
      `- ✅ Shared asset management`,
      `- ✅ Proper heading hierarchy`,
      `- ✅ Code block preservation`,
      `- ✅ Table formatting`,
      ``,
      `## Usage`,
      ``,
      `Navigate through the markdown files to read the documentation offline.`,
      `All internal links have been converted to absolute URLs pointing to the original site.`
    ].join('\n');

    await fs.writeFile(indexPath, indexContent);
    console.log(`\n✓ Created index file: ${indexPath}`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const baseUrl = args[0] || 'https://docs.n8n.io/';
  const outputDir = args[1] || path.join(process.cwd(), 'data', 'scraped_docs');

  // Parse options
  const options = {
    maxConcurrency: args.includes('--concurrency') ?
      parseInt(args[args.indexOf('--concurrency') + 1], 10) : 2,
    delay: args.includes('--delay') ?
      parseInt(args[args.indexOf('--delay') + 1], 10) : 2000,
    maxPages: args.includes('--max-pages') ?
      parseInt(args[args.indexOf('--max-pages') + 1], 10) : 500,
    downloadAssets: !args.includes('--no-assets'),
    preserveImageSizes: !args.includes('--no-preserve-sizes'),
    maxImageWidth: args.includes('--max-width') ?
      parseInt(args[args.indexOf('--max-width') + 1], 10) : 800
  };

  console.log('=== Full Site Markdown Scraper ===');
  console.log(`Base URL: ${baseUrl}`);
  console.log(`Output Directory: ${outputDir}`);
  console.log(`Options: ${JSON.stringify(options, null, 2)}`);

  try {
    const scraper = new FullSiteMarkdownScraper(baseUrl, outputDir, options);
    await scraper.scrapeFullSite();
    console.log('\n🎉 Full site scraping completed successfully!');
  } catch (error) {
    console.error('\n❌ Scraping failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { FullSiteMarkdownScraper };