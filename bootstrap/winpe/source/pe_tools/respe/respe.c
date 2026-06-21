#pragma comment(lib, "user32.lib")
#include <windows.h>
#include <stdio.h>

int wmain(int argc, wchar_t* argv[])
{
  if (argc < 3)
  {
    wprintf(L"Usage: respe.exe <width> <height> [bits]\n");
    return 1;
  }

  int width = _wtoi(argv[1]);
  int height = _wtoi(argv[2]);
  int bits = (argc >= 4) ? _wtoi(argv[3]) : 32;

  DEVMODEW dm;
  ZeroMemory(&dm, sizeof(dm));
  dm.dmSize = sizeof(dm);

  if (!EnumDisplaySettingsW(NULL, ENUM_CURRENT_SETTINGS, &dm))
  {
    wprintf(L"Failed to get current display settings\n");
    return 1;
  }

  dm.dmPelsWidth = width;
  dm.dmPelsHeight = height;
  dm.dmBitsPerPel = bits;

  dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL;

  LONG result = ChangeDisplaySettingsExW(NULL, &dm, NULL, CDS_FULLSCREEN, NULL);

  switch (result)
  {
    case DISP_CHANGE_SUCCESSFUL:
      wprintf(L"Resolution changed to %dx%d (%d-bit)\n", width, height, bits);
      return 0;

    case DISP_CHANGE_BADMODE:
      wprintf(L"Unsupported resolution\n");
      return 2;

    case DISP_CHANGE_RESTART:
      wprintf(L"Restart required\n");
      return 3;

    default:
      wprintf(L"Failed (code %ld)\n", result);
      return 4;
  }
}