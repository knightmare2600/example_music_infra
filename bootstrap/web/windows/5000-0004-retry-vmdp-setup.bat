echo Retry v2v firstboot VMDP installation
echo Force extraction of VMDP installation files
"\vmdp.exe" -y
pushd "VMDP-*"
echo Running setup.exe /eula_accepted /no_reboot
setup.exe /eula_accepted /no_reboot
popd
