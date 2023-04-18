package main

import (
	"bufio"
	"fmt"
	"log"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/net/html"

	"github.com/gocolly/colly/v2"
)

func main() {
	if len(os.Args) != 2 {
		log.Fatalln("Usage: ./main <config_file>")
	}

	configFilename := os.Args[1]

	// Check if the config file exists
	if _, err := os.Stat(configFilename); os.IsNotExist(err) {
		log.Fatalf("Config file %s does not exist.", configFilename)
	}

	file, err := os.Open(configFilename)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		entry := scanner.Text()
		if isURL(entry) {
			crawlWebsite(entry)
		} else {
			processLocalGitFolder(entry)
		}
	}

	if err := scanner.Err(); err != nil {
		log.Fatal(err)
	}
}

func isURL(str string) bool {
	u, err := url.Parse(str)
	return err == nil && u.Scheme != "" && u.Host != ""
}

func crawlWebsite(rootURL string) {
	outputDir := "./output" + string(os.PathSeparator) + getDomain(rootURL)
	_ = os.MkdirAll(outputDir, os.ModePerm)

	c := colly.NewCollector(
		colly.AllowedDomains(getDomain(rootURL)),
		colly.Async(true),
		colly.CacheDir("./colly_cache"),
	)

	c.OnHTML("a[href]", func(e *colly.HTMLElement) {
		link := e.Attr("href")
		_ = e.Request.Visit(link)
	})

	c.OnResponse(func(r *colly.Response) {
		urlPath := r.Request.URL.Path

		fileName := fmt.Sprintf("%s.txt", strings.Replace(urlPath, "/", "_", -1))

		filePath := filepath.Join(outputDir, fileName)
		_ = os.MkdirAll(filepath.Dir(filePath), os.ModePerm)

		textContent := extractTextContent(string(r.Body))
		if len(strings.TrimSpace(textContent)) == 0 {
			return
		}

		err := os.WriteFile(filePath, []byte(textContent), 0644)
		if err != nil {
			log.Printf("Failed to write file: %s\n", err)
		}
	})

	err := c.Visit(rootURL)
	if err != nil {
		log.Fatal(err)
	}

	c.Wait()
}

func processLocalGitFolder(folderPath string) {
	if _, err := os.Stat(folderPath); os.IsNotExist(err) {
		log.Printf("Local git folder does not exist: %s\n", folderPath)
		return
	}
	// Add any additional processing for local git folders here
}

func getDomain(rawURL string) string {
	parsedURL, err := url.Parse(rawURL)
	if err != nil {
		log.Fatalf("Error parsing URL: %s\n", err)
	}
	return parsedURL.Host
}

func extractTextContent(body string) string {
	var textContent string
	z := html.NewTokenizer(strings.NewReader(body))

	inScript := false

	for {
		tt := z.Next()

		switch tt {
		case html.ErrorToken:
			return textContent
		case html.TextToken:
			if !inScript {
				textContent += strings.TrimSpace(string(z.Text())) + " "
			}
		case html.StartTagToken, html.EndTagToken:
			tagName, _ := z.TagName()
			if string(tagName) == "script" {
				if tt == html.StartTagToken {
					inScript = true
				} else {
					inScript = false
				}
			}
		}
	}
}
