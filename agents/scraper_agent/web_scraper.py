from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json
import time

def scrape_dynamic_webpage(url):
    """
    Scrape content from a webpage that loads content dynamically
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        dict: Scraped content
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-dev-shm-usage', '--no-sandbox']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        page = context.new_page()
        
        try:
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(60000)
            
            print("Navigating to page...")
            response = page.goto(url, wait_until='networkidle', timeout=60000)
            
            if response is None or not response.ok:
                return {'error': f"Failed to load page. Status: {response.status if response else 'Unknown'}"}
            
            print("Waiting for content to load...")
            try:
                page.wait_for_selector('main, #root, #__next, .main-content', timeout=60000)
            except PlaywrightTimeout:
                print("Warning: Timeout waiting for main content selector, continuing anyway...")
            
            time.sleep(5)
            
            print("Extracting content...")
            content = {
                'title': '',
                'metadata': {},
                'bounty_info': {},
                'content': [],
                'links': []
            }
            
            content['title'] = page.title()
            
            # Get metadata
            for meta in page.query_selector_all('meta'):
                name = meta.get_attribute('name')
                if name:
                    content['metadata'][name] = meta.get_attribute('content')
            
            # Extract content with preserved formatting
            content['content'] = page.evaluate('''
                () => {
                    function isVisible(element) {
                        if (!element) return false;
                        const style = window.getComputedStyle(element);
                        return style.display !== 'none' && 
                               style.visibility !== 'hidden' && 
                               style.opacity !== '0';
                    }

                    function processElement(element) {
                        if (!isVisible(element)) return null;
                        
                        // Skip script and style elements
                        if (element.tagName === 'SCRIPT' || element.tagName === 'STYLE') return null;
                        
                        // Check if this is a code block
                        const isCodeBlock = element.tagName === 'PRE' || 
                                          element.tagName === 'CODE' ||
                                          element.classList.contains('code') ||
                                          element.classList.contains('pre') ||
                                          element.classList.contains('language-python') ||
                                          element.closest('pre') !== null ||
                                          element.querySelector('code') !== null;
                        
                        if (isCodeBlock) {
                            // For code blocks, preserve exact formatting
                            return {
                                type: 'code',
                                filename: element.previousElementSibling?.textContent || '',
                                content: element.textContent,
                                language: Array.from(element.classList)
                                    .find(cls => cls.startsWith('language-'))
                                    ?.replace('language-', '') || 'python'
                            };
                        }
                        
                        // For headings
                        if (element.tagName.match(/^H[1-6]$/)) {
                            return {
                                type: 'heading',
                                content: element.textContent.trim()
                            };
                        }
                        
                        // For regular text content
                        const textContent = element.textContent.trim();
                        if (textContent) {
                            return {
                                type: 'text',
                                content: textContent
                            };
                        }
                        
                        return null;
                    }

                    function extractContent(root) {
                        const sections = [];
                        
                        // Process all direct children
                        for (const child of root.children) {
                            const content = processElement(child);
                            if (content) {
                                sections.push(content);
                            }
                            
                            // If this element has children and isn't a code block,
                            // process them too
                            if (child.children.length > 0 && 
                                !content?.type === 'code') {
                                sections.push(...extractContent(child));
                            }
                        }
                        
                        return sections;
                    }
                    
                    // Get content from main content areas
                    const contentAreas = document.querySelectorAll('main, article, .content, .main-content');
                    if (contentAreas.length > 0) {
                        return Array.from(contentAreas)
                            .map(area => extractContent(area))
                            .flat()
                            .filter(section => section !== null);
                    }
                    
                    // Fallback to body
                    return extractContent(document.body)
                        .filter(section => section !== null);
                }
            ''')
            
            # Get links
            links = page.query_selector_all('a')
            content['links'] = [
                {
                    'text': link.inner_text().strip(),
                    'href': link.get_attribute('href')
                }
                for link in links
                if link.get_attribute('href')
            ]
            
            # Try to get bounty-specific information
            try:
                selectors = {
                    'title': 'h1, .bounty-title',
                    'status': '.status, .bounty-status',
                    'severity': '.severity',
                    'description': '.description, .bounty-description',
                    'reward': '.reward, .bounty-reward'
                }
                
                content['bounty_info'] = {
                    key: page.query_selector(selector).inner_text().strip() if page.query_selector(selector) else ''
                    for key, selector in selectors.items()
                }
            except Exception as e:
                print(f"Warning: Error extracting bounty info: {str(e)}")
            
            return content
            
        except PlaywrightTimeout as e:
            return {'error': f"Timeout error: {str(e)}"}
        except Exception as e:
            return {'error': f"Error scraping {url}: {str(e)}"}
        finally:
            browser.close()

def main():
    url = "https://huntr.com/bounties/486add92-275e-4a7b-92f9-42d84bc759da"
    print(f"Starting to scrape {url}")
    content = scrape_dynamic_webpage(url)
    
    # Print the results in a readable format
    print(json.dumps(content, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()