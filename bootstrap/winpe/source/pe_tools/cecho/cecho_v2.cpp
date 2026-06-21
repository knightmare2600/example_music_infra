/*
  -----------------------------------------------------------------------------
  cecho.cpp - Minimal Color Echo Utility (WinPE / CMD Safe)
  -----------------------------------------------------------------------------

  Version:  1.3.0
  Author:   Knightmare2600
  License:  MIT-style (do whatever you want)

  Description: A tiny console utility for Windows that prints coloured text
               using embedded tokens. Designed for WinPE, batch scripts, and
               deployment environments where ANSI is unreliable.

  Features:
    - Inline colour changes: {0A}, {0F}, etc.
    - Reset colour: {##} or {reset}
    - Newlines: {n}, {NL}, {CRLF}, {\n}
    - CMD-safe parsing (no fragile escaping)
    - Works with MSVC and MinGW (x86/x64/ARM64)
    - No external dependencies

  Example:
    cecho.exe "{03}Hello {0F}World{n}{##}"

  ---------------------------------------------------------------------------
*/

#include <windows.h>
#include <iostream>
#include <string>
#include <cctype>
#include <cstdlib>

// Global default console colour
static WORD g_defaultColor = 7;

// Convert hex string (e.g. "0A") to Windows console colour
WORD HexToColor(const std::string& hex) {
  return (WORD)strtol(hex.c_str(), nullptr, 16);
}

// Flatten all CLI arguments into a single string (prevents CMD argument splitting issues)
std::string ReadArgs(int argc, char* argv[]) {
  std::string input;
  for (int i = 1; i < argc; i++) {
    input += argv[i];
    if (i < argc - 1) input += " ";
  }
  return input;
}

/**
  Core parser:
  - Handles colour tokens
  - Handles newline tokens
  - Tolerates CMD mangling
**/
void Process(const std::string& input, HANDLE hConsole) {
  for (size_t i = 0; i < input.size();) {
    // Token handling
    if (input[i] == '{') {
      // ---- NEWLINE TOKENS ----
      if (i + 2 < input.size() && input.substr(i, 3) == "{n}") {
        std::cout << "\r\n";
        i += 3;
        continue;
      }
      if (i + 3 < input.size() && input.substr(i, 4) == "{NL}") {
        std::cout << "\r\n";
        i += 4;
        continue;
      }
      if (i + 5 < input.size() && input.substr(i, 6) == "{CRLF}") {
        std::cout << "\r\n";
        i += 6;
        continue;
      }
      // Legacy {\n}
      if (i + 3 < input.size() && input.substr(i, 4) == "{\\n}") {
        std::cout << "\r\n";
        i += 4;
        continue;
      }
      // ---- RESET ----
      if (i + 3 < input.size() && input.substr(i, 4) == "{##}") {
        SetConsoleTextAttribute(hConsole, g_defaultColor);
        i += 4;
        continue;
      }
      if (i + 6 < input.size() && input.substr(i, 7) == "{reset}") {
        SetConsoleTextAttribute(hConsole, g_defaultColor);
        i += 7;
        continue;
      }
      // ---- COLOUR {0A} ----
      if (i + 3 < input.size() && input[i + 3] == '}') {
        std::string code = input.substr(i + 1, 2);

        if (isxdigit(code[0]) && isxdigit(code[1])) {
          WORD color = HexToColor(code);
          SetConsoleTextAttribute(hConsole, color);
          i += 4;
          continue;
        }
      }
      // ---- ESCAPED LITERAL {{ ----
      if (i + 1 < input.size() && input[i + 1] == '{') {
        std::cout << "{";
        i += 2;
        continue;
      }
    }
    // Default: print character
    std::cout << input[i];
    i++;
  }
}

// Entry point
int main(int argc, char* argv[]) {
  HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);

  // Save default console colour
  CONSOLE_SCREEN_BUFFER_INFO csbi;
  GetConsoleScreenBufferInfo(hConsole, &csbi);
  g_defaultColor = csbi.wAttributes;

  // Read input
  std::string input = ReadArgs(argc, argv);
  if (input.empty()) return 0;

  // Process input
  Process(input, hConsole);

  // Restore default colour
  SetConsoleTextAttribute(hConsole, g_defaultColor);
  return 0;
}