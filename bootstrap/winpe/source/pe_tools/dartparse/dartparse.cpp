/********************************************************************************
 * dartparse.cpp                                                                *
 * Minimal DaRT XML helper for WinPE                                            *
 * GPL-3.0 License                                                              *
 *                                                                              *
 * Features:                                                                    *
 *  /f <file>   XML file to parse (required)                                    *
 *  /p          Pretty print XML                                                *
 *  /d          Decode attributes (key: value)                                  *
 *  /g <key>    Grep attribute by key                                           *
 *  /b          Bare output (values only)                                       *
 *  /ip         Output all IPs (N attributes)                                   *
 *  /rdp        Output ip:port pairs where P="3389"                             *
 *  /env        Emit CMD-friendly set VAR=value lines                           *
 *  /?          Help                                                            *
 *                                                                              *
 * Examples:                                                                    *
 *  dartparse /f inv32.xml /g ID                                                *
 *  dartparse /f inv32.xml /g ID /b                                             *
 *  dartparse /f inv32.xml /d                                                   *
 *  dartparse /f inv32.xml /ip                                                  *
 *  dartparse /f inv32.xml /rdp                                                 *
 *  dartparse /f inv32.xml /env                                                 *
 *                                                                              *
 * Build (MSVC - Developer Command Prompt):                                     *
 *  cl /O2 /EHsc dartparse.cpp                                                  *
 *                                                                              *
 * Build (MinGW):                                                               *
 *  g++ -O2 -static -s -o dartparse.exe dartparse.cpp                           *
 *                                                                              *
 * Notes:                                                                       *
 *  - No external dependencies (WinPE safe)                                     *
 *  - Regex-based (not full XML parser)                                         *
 ********************************************************************************/

#include <windows.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

// Read entire file into string
std::string ReadFile(const std::string& path) {
  std::ifstream file(path);
  if (!file) return "";
  std::ostringstream ss;
  ss << file.rdbuf();
  return ss.str();
}

// Extract value of attribute KEY="value"
std::string GetAttr(const std::string& xml, const std::string& key) {
  std::string search = key + "=\"";
  size_t pos = xml.find(search);
  if (pos == std::string::npos) return "";
  pos += search.length();
  size_t end = xml.find("\"", pos);
  if (end == std::string::npos) return "";
  return xml.substr(pos, end - pos);
}

// Decode all attributes (simple scan)
void Decode(const std::string& xml, bool bare) {
  size_t pos = 0;
  while ((pos = xml.find('=', pos)) != std::string::npos) {
    size_t keyStart = xml.rfind(' ', pos);
    if (keyStart == std::string::npos) keyStart = xml.rfind('<', pos);
    if (keyStart == std::string::npos) break;
    keyStart++;

    std::string key = xml.substr(keyStart, pos - keyStart);

    size_t valStart = xml.find('"', pos);
    if (valStart == std::string::npos) break;
    valStart++;

    size_t valEnd = xml.find('"', valStart);
    if (valEnd == std::string::npos) break;

    std::string val = xml.substr(valStart, valEnd - valStart);

    if (bare) std::cout << val << "\n";
    else std::cout << key << ": " << val << "\n";

    pos = valEnd;
  }
}

// Extract all IPs (N="...")
void GetIPs(const std::string& xml) {
  size_t pos = 0;
  while ((pos = xml.find("N=\"", pos)) != std::string::npos) {
    pos += 3;
    size_t end = xml.find("\"", pos);
    if (end == std::string::npos) break;
    std::cout << xml.substr(pos, end - pos) << "\n";
    pos = end;
  }
}

// Extract RDP endpoints (P="3389" + N="...")
void GetRDP(const std::string& xml) {
  size_t pos = 0;
  while ((pos = xml.find("P=\"3389\"", pos)) != std::string::npos) {
    size_t npos = xml.find("N=\"", pos);
    if (npos == std::string::npos) break;
    npos += 3;
    size_t end = xml.find("\"", npos);
    if (end == std::string::npos) break;
    std::cout << xml.substr(npos, end - npos) << ":3389\n";
    pos = end;
  }
}

void Usage() {
  std::cout << "dartparse - minimal WinPE XML helper (GPL-3.0)\n\n";

  std::cout << "Usage:\n";
  std::cout << "  dartparse /f <file> [options]\n\n";

  std::cout << "Options:\n";
  std::cout << "  /f <file>   XML file to parse (required)\n";
  std::cout << "  /p      Pretty print XML (basic formatting)\n";
  std::cout << "  /d      Decode attributes (key: value)\n";
  std::cout << "  /g <key>  Find attribute by key (e.g. ID, KH, N, P)\n";
  std::cout << "  /b      Bare output (values only, no labels)\n";
  std::cout << "  /ip     Output all IPs (N attributes)\n";
  std::cout << "  /rdp    Output RDP endpoints (ip:3389)\n";
  std::cout << "  /?      Show this help\n\n";

  std::cout << "Example XML (single line):\n";
  std::cout << "  <A KH=\"abc\" ID=\"161-742-045\"/><C><T><L P=\"3389\" N=\"192.168.1.10\"/></T></C>\n\n";

  std::cout << "Examples:\n";
  std::cout << "  dartparse /f inv32.xml /g ID\n";
  std::cout << "  dartparse /f inv32.xml /g ID /b\n";
  std::cout << "  dartparse /f inv32.xml /d\n";
  std::cout << "  dartparse /f inv32.xml /ip\n";
  std::cout << "  dartparse /f inv32.xml /rdp\n\n";

  std::cout << "Notes:\n";
  std::cout << "  - Designed for WinPE (x86/x64/ARM64)\n";
  std::cout << "  - No external dependencies\n";
  std::cout << "  - Simple string parsing (not a full XML parser)\n";
}


int main(int argc, char* argv[]) {
  std::string file, key;
  bool decode=false, bare=false, ip=false, rdp=false;

  for (int i=1;i<argc;i++){
    std::string a=argv[i];
    if(a=="/?"){Usage();return 0;}
    else if(a=="/f"&&i+1<argc) file=argv[++i];
    else if(a=="/d") decode=true;
    else if(a=="/g"&&i+1<argc) key=argv[++i];
    else if(a=="/b") bare=true;
    else if(a=="/ip") ip=true;
    else if(a=="/rdp") rdp=true;
  }

  if(file.empty()){std::cout<<"No file specified\n";return 1;}

  std::string xml=ReadFile(file);
  if(xml.empty()){std::cout<<"XML not found\n";return 1;}

  if(decode) Decode(xml,bare);

  if(!key.empty()){
    std::string val = GetAttr(xml,key);
    if(val.empty()) std::cout<<"Value not found: "<<key<<"\n";
    else if(bare) std::cout<<val<<"\n";
    else std::cout<<key<<": "<<val<<"\n";
  }

  if(ip) GetIPs(xml);
  if(rdp) GetRDP(xml);

  return 0;
}
