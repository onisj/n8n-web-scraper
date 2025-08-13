// Full site scraper for https://docs.n8n.io/
const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');
const https = require('https');
const http = require('http');
const { URL } = require('url');

class FullSiteScraper {
  constructor(baseUrl, outputDir) {
    this.baseUrl = baseUrl;
    this.outputDir = outputDir;
    this.visitedUrls = new Set();
    this.urlQueue = [];
    this.scrapedCount = 0;
    this.errorCount = 0;
    this.maxConcurrency = 3; // Limit concurrent requests
    this.delay = 1000; // Delay between requests (ms)
    this.maxPages = 500; // Safety limit
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

  // Generate filename from URL
  generateFilename(url) {
    try {
      const urlObj = new URL(url);
      let pathname = urlObj.pathname;
      
      // Remove leading slash and replace slashes with underscores
      pathname = pathname.replace(/^\//, '').replace(/\//g, '_');
      
      // Handle root path
      if (!pathname || pathname === '') {
        pathname = 'index';
      }
      
      // Remove trailing underscore
      pathname = pathname.replace(/_$/, '');
      
      return `${pathname}.json`;
    } catch (error) {
      return `page_${Date.now()}.json`;
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

  // Scrape a single page
  async scrapePage(url, browser) {
    const page = await browser.newPage();
    
    try {
      console.log(`Scraping: ${url}`);
      
      // Set user agent and viewport
      await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
      await page.setViewport({ width: 1200, height: 800 });
      
      // Navigate to page
      await page.goto(url, { 
        waitUntil: 'networkidle2', 
        timeout: 30000 
      });
      
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
        
        // Extract structured data
        const headings = Array.from(mainContent.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(h => ({
          level: parseInt(h.tagName.charAt(1)),
          text: h.textContent.trim(),
          id: h.id || ''
        }));
        
        const links = Array.from(mainContent.querySelectorAll('a[href]')).map(a => ({
          text: a.textContent.trim(),
          href: a.href,
          title: a.title || ''
        }));
        
        const images = Array.from(mainContent.querySelectorAll('img')).map(img => ({
          src: img.src,
          alt: img.alt || '',
          title: img.title || ''
        }));
        
        const codeBlocks = Array.from(mainContent.querySelectorAll('pre, code')).map(code => ({
          language: code.className.match(/language-(\w+)/)?.[1] || '',
          content: code.textContent.trim()
        }));
        
        return {
          url: window.location.href,
          title: document.title,
          content: mainContent.textContent.trim(),
          content_html: mainContent.innerHTML,
          headings: headings,
          links: links,
          images: images,
          code_blocks: codeBlocks,
          metadata: {
            scraped_at: new Date().toISOString(),
            word_count: mainContent.textContent.trim().split(/\s+/).length,
            character_count: mainContent.textContent.trim().length
          }
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
      
      // Save content to file
      const filename = this.generateFilename(url);
      const filepath = path.join(this.outputDir, filename);
      await fs.writeFile(filepath, JSON.stringify(content, null, 2));
      
      this.scrapedCount++;
      console.log(`✓ Scraped: ${url} -> ${filename} (${this.scrapedCount} total)`);
      
      return content;
      
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
    console.log(`Starting full site scrape of: ${this.baseUrl}`);
    console.log(`Output directory: ${this.outputDir}`);
    
    // Ensure output directory exists
    await fs.mkdir(this.outputDir, { recursive: true });
    
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
        
        // Add delay between batches
        if (this.urlQueue.length > 0) {
          await new Promise(resolve => setTimeout(resolve, this.delay));
        }
        
        // Progress update
        console.log(`Progress: ${this.visitedUrls.size} pages visited, ${this.urlQueue.length} in queue`);
      }
      
      const endTime = Date.now();
      const duration = Math.round((endTime - startTime) / 1000);
      
      // Generate summary
      const summary = {
        scraping_completed_at: new Date().toISOString(),
        base_url: this.baseUrl,
        output_directory: this.outputDir,
        total_pages_scraped: this.scrapedCount,
        total_errors: this.errorCount,
        total_urls_discovered: this.visitedUrls.size,
        duration_seconds: duration,
        pages_per_second: Math.round(this.scrapedCount / duration * 100) / 100
      };
      
      // Save summary
      const summaryPath = path.join(this.outputDir, 'scraping_summary.json');
      await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2));
      
      console.log('\n=== Scraping Complete ===');
      console.log(`Pages scraped: ${this.scrapedCount}`);
      console.log(`Errors: ${this.errorCount}`);
      console.log(`Duration: ${duration}s`);
      console.log(`Average: ${summary.pages_per_second} pages/second`);
      console.log(`Summary saved to: ${summaryPath}`);
      
      return summary;
      
    } finally {
      await browser.close();
    }
  }
}

// Main execution function
async function main() {
  const baseUrl = process.argv[2] || 'https://docs.n8n.io/';
  const outputDir = process.argv[3] || path.join(__dirname, 'data', 'scraped_docs');
  
  console.log('=== Full Site Scraper ===');
  console.log(`Base URL: ${baseUrl}`);
  console.log(`Output Directory: ${outputDir}`);
  
  const scraper = new FullSiteScraper(baseUrl, outputDir);
  
  try {
    await scraper.scrapeFullSite();
    process.exit(0);
  } catch (error) {
    console.error('Scraping failed:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { FullSiteScraper };