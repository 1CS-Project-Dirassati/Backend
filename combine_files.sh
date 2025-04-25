#!/bin/bash

output_file="combined_output.txt"

# Empty or create the output file
> "$output_file"

for file in *; do
    if [ -f "$file" ] && [ "$file" != "$output_file" ]; then
        echo "Processing: $file"

        # Write filename header
        echo "===== $file =====" >> "$output_file"

        # Append file content
        cat "$file" >> "$output_file"

        # Add a newline separator
        echo -e "\n" >> "$output_file"
    fi
done

echo "Files combined into $output_file"

