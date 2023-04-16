package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

func main() {
	if len(os.Args) != 2 {
		log.Fatal("Usage: ./df <root_url>")
	}

	domain := os.Args[1]
	fmt.Println(domain)

	var texts []TextData
	//textDir := filepath.Join("output", domain)
	textDir := filepath.Join("..", "output")

	files, err := os.ReadDir(textDir)
	if err != nil {
		fmt.Println("Error reading directory:", err)
		return
	}

	for _, file := range files {
		fileName := file.Name()
		if !file.IsDir() && filepath.Ext(fileName) == ".txt" {
			textBytes, err := os.ReadFile(filepath.Join(textDir, fileName))
			if err != nil {
				fmt.Println("Error reading file:", err)
				continue
			}

			text := string(textBytes)
			modifiedFilename := strings.ReplaceAll(strings.ReplaceAll(strings.ReplaceAll(fileName[11:len(fileName)-4], "-", " "), "_", " "), "#update", " ")
			texts = append(texts, TextData{Fname: modifiedFilename, Text: modifiedFilename + ". " + removeNewlines(text)})
			println("Processed", fileName, "with", len(text), "characters", "and modified filename:", modifiedFilename)
		}
	}

	writeCSV(texts)
}

type TextData struct {
	Fname string
	Text  string
}

func removeNewlines(text string) string {
	re := regexp.MustCompile(`\n|\\n| {2}`)
	return re.ReplaceAllString(text, " ")
}

func writeCSV(texts []TextData) {
	file, err := os.Create("../processed/scraped.csv")
	if err != nil {
		fmt.Println("Error creating file:", err)
		return
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	err = writer.Write([]string{"fname", "text"})
	if err != nil {
		fmt.Println("Error writing header:", err)
		return
	}

	for _, textData := range texts {
		err := writer.Write([]string{textData.Fname, textData.Text})
		if err != nil {
			fmt.Println("Error writing record:", err)
		}
	}
}
