
" Creator: Pento <naplanetu[at]gmail.com>
" Maintainer: Knightmare <knightmare[at]hackthebox.eu>
" Version: 31JAN2013_001

"------------------------------------------------------------------------------
" This vim file will syntax highlight your nmap output when piped to a file.  -
" to a file.  Best put it in ~/.vim/syntax/nmap.vim and then call it with     -
" :set syntax=nmap in vim.                                                    -
"                                                                             -
" A word on updates:                                                          -
" Used NMap SVN. Hand edited device-types.txt adding the device types in. On  -
" nmap-os-db, nmap-services I cat $file | awk '{ print $1 }' | sort | uniq    -
" with some hand editing to make things work.  Not pretty, but does the job.  -
"                                                                             -
" Version History:                                                            -
" 10 Nov 2009  Pento          Inital Version Copyright unknown                -
" 26 Jan 2013  Knightmare     Started rewrite: added protocols                -
" 27 Jan 2013  Knightmare     Update to highlight times/dates/MAC addresses   -
" 28 Jan 2013  Knightmare     Add <-- comment and - in protocol names	      -
" 28 Jan 2013  Knightmare     Add proper colours when highlighting            -
" 28 Jan 2013  Knightmare     More colours, add missing protocols, Dark Red   -
"                             Errors/Warnings to stand out, mark OS Guess too -
" 28 Jan 2013  Knightmare     Mark Unknown Fingerprints and NSE outout        -
" 29 Jan 2013  Knightmare     Add protocols, white times and nmap done line   -
" 29 Jan 2013  Knightmare     OS and Service detection now highlightsi        -
" 29 Jan 2013  Knightmare     Update device, protocol and time lists          -
" 30 Jan 2013  Knightmare     Mark retro/funny/odd Fingerprints. This is not  -
"                             to detect them, just highlight unusual ones...  -
" 31 Jan 2013  Knightmare     Mark more retro/funny/odd devices, e.g. TVs     -
"------------------------------------------------------------------------------

" TODO: Add script output highlighting, which is multi line
" TODO: Split up protocols so they are on 26 lines to make life easier

if version < 600 
    syntax clear
elseif exists("b:current_syntax")
    finish
endif

" Nmap is fond of using hyphens in protocol names, e.g. netbios-ssn so match that too
setlocal iskeyword+=-

syntax sync fromstart

" Highlight NMap banners
syn region nmapBanner start="^Starting Nmap" end="at"
syn region nmapNSE start="^NSE" end=".*"
syn region nmapReport start="^Nmap scan report" end="for"
syn keyword nmapStatement PORT STATE SERVICE VERSION TRACEROUTE ADDRESS HOP RTT 
syn match nmapComment "#.*$"
syn region nmapOSDetection start="OS and Service detection" end="at\s"
syn region nmapDone start="Nmap done:" end="[0-9]\.\s"

" Port numbers and Status
syn match nmapPort "^\d\+/"
syn keyword nmapPortStatusGood open unfiltered
syn keyword nmapPortStatusBad closed filtered

" Dates and times and the adjectives they use
syn keyword nmapTimePeriod hour hours minute minutes second seconds day days GMT DST UTC BST Mon Tue Wed Thu Fri Sat Sun latency
syn match nmapDate "[0-9][0-9][0-9][0-9]\-[.0-9_]*\-[0-9][0-9]"
syn match nmapTime "([0-1]?[0-9]|2[0-4]):([0-5][0-9])(:[0-5][0-9])?$"
syn match nmapScanTime "[0-2][0-9]\:[0-5][0-9]"

" Hightlight OS, OS version, CPE and Service info lines
syn region nmapOSDetails start='^OS details:' end='\s'
syn region nmapOSRunning start='^Running' end='.*'
syn region nmapOSRunning start="^Aggressive OS" end="guesses:"
syn region nmapOSCPE start='^OS CPE:' end='.*'
syn region nmapServiceInfo start='Service Info:' end='.*'

" IPs, Hostnames, MACs, TCP sequence and device types
syn match nmapIP "\d\+\.\d\+\.\d\+\.\d\+"
syn match nmapHostName "[a-zA-Z0-9._-]\+\.[a-zA-Z]\{2,3}"
syn match nmapMACAddress "^([0-9a-fA-F][0-9a-fA-F]:){5}([0-9a-fA-F][0-9a-fA-F])$"
"syn match nmapMACAddress "/^([0-9a-fA-F]{1,2}[\.:-]){5}([0-9a-fA-F]{1,2})$/i"
syn keyword nmapTCPPrediction Trivial joke Easy Medium Formidable Worthy challenge Good luck!
syn region nmapDeviceTypeLine start="^Device type" end="\s"
syn keyword nmapDeviceType firewall general purpose hub load balancer media device PBX PDA phone power-device printer print server proxy server remote managment router security-misc specialized storage-misc switch telecom-misc terminal terminal server VoIP adapter VoIP phone WAP webcam 

" Highlight URLs working on the premise URLs don't include spaces
syn region nmapURL start="http://" end=" "

" Warnings and errors
syn region nmapErrorWarning start="Warning:" end=".*"
syn region nmapErrorWarning start="Too many fingerprints match this host to give specific OS" end="details"
syn region nmapErrorWarning start="^[0-65535] services unrecognized" end=".*"

" When NMap doesn't know what's going on, it offers to submit a fingerprint
syn region nmapSubmit start="^==============NEXT" end=".*"
syn region nmapSubmit start="^SF-" end=".*"
syn region nmapSubmit start="^SF:" end=".*"

" My own Modus Operandi, use <-- as a comment line. Puts it black on a 
" yellow background if you set it's HiLink as TODO
syn region nmapKnightmareComment start='<--' end='.*'

" Script output. Need to do some better regex though
syn region nmapScriptOutput start='^|' end='.*'

""syn match nmapProto "/\%3c./"
syn region nmapProto start="3com-amp3 3comfaxrpc 3com-net-mgmt 3com-njack-1 3com-tsmux 3d-nfsd 3ds-lm 3exmp 3link 3l-l1 3m-image-lm 802-11-iapp 914c-g 9pfs" end=" "
syn region nmapProto start="a17-an-an a26-fap-fgw aairnet-2 aal-lm aap abarsd abatjss abbaccuray abcsoftware about abr-api abyss acap acas accelenet accessbuilder accessnetwork acc-raid accuracer ace-client ace-proxy aci acmaint_dbd acmaint_transd acms acmsoda acp acp-conduit acp-policy acp-proto acr-nema active-net activesync activesync-notify adap adapt-sna admd admdog admeng admind admins-lms adobeserver-1 adobeserver-2 adobeserver-3 ads advocentkvm aed-512 aegate aeroflight-ads af afesc-mc affiliate afp afrog afs afs3-bos afs3-callback afs3-errors afs3-fileserver afs3-kaserver afs3-prserver afs3-rmtsys afs3-update afs3-vlserver afs3-volser agcat agentsease-db agentx agps-port ah-esp-encap aiagent aibkup aimpp-port-req aipn-reg airport-admin airs airshot ajp12 ajp13 alarm-clock-s alesquery alias allstorcns alpes alta-ana-lm altav-remmgt altav-tunnel altbsdp altcp altovacentral amanda amandaidx amdsched amidxtape amiganetfs amp ampify ampr-info ampr-inter ampr-rcmd amqp ams amt-cnf-prot amt-esd-prot amt-soap-http amt-soap-https amx-icsp amx-rms amx-weblinx analogx and-lm anet anet-l an-pcp ansanotify ansatrader ans-console ansoft-lm-1 ansoft-lm-2 ansysli ansys-lm ansyslmd anthony-data antidotemgrsvr anynetgateway aocp aodv aol aol-1 aol-2 aol-3 ap apani1 apani2 apani5 apc-2160 apc-2161 apc-2260 apc-3052 apc-3506 apc-7846 apc-9950 apc-9952 apc-agent apc-necmp apcupsd apdap apertus-ldp apex-edge apex-mesh aplx apm-link apocd apple-imap-admin apple-iphoto apple-licman appleqtc appleqtcsrvr apple-sasl apple-vpns-rp apple-xsrvr-admin appliance-cfg applix applusservice appserv-http appss-lm appworxsrv apri-lm apwi-disc apx500api-1 apx500api-2 arcisdms arcpd arcserve ardt ardus-cntl ardus-mtrns ardusmul ardusuni arepa-cas argis-ds ariel1 ariel2 ariel3 arns asa asa-appl-proto asam asap-sctp asap-sctp-tls asap-tcp asci-val ascomalarm as-debug asf-rmcp asi asipregistry asip-webadmin asnaacceler8db aspeclmd aspentec-lm asprovatalk asr as-servermap assuria-slm asterix astromed-main at-3 at-5 at-7 at-8 atc-lm at-echo atex_elmd atls atmtcp atm-zip-office at-nbp at-rtmp ats attachmate-g32 attachmate-uts at-zis audio-activmail audiojuggler audionews audit auditd audit-transfer aurora aurora-cmgr aurp auth autocuesmi autocuetime autodesk-lm autodesk-nlm availant-mgr avantageb2b avanti_cdp avenue avian avocent-adsap avocent-proxy avsecuremgmt avt-profile-1 avt-profile-2 axis-wimp-port axon-lm azeti" end=" "
" b2n b2-runtime babel backburner BackOrifice backupedge backupexec backup-express bacnet bacula-dir bacula-sd bakbonenetvault banyan-net banyan-rpc banyan-vip bb bbn-mmc bbn-mmx bcinameservice bcslogc bctp bdp bears-02 beorl BESApi beserver-msg-q bex-webadmin bex-xr beyond-remote bfd-control bfd-multi-ctl bftp bgmp bgp bgpd bh611 bhevent bhfhs bhmds biap-mp biff bigbrother biimenu bim-pem binderysupport binkp bintec-capi bip"
" bittorrent-tracker blackboard blackice-alerts blackice-icecap blackjack blaze bl-idm blp3 blp4 blueberry-lm bluelance blwnkl-port bmap bmc-ar bmc-ea bmc-messaging bmc-perf-agent bmpp bnet bnetfile bnetgame bo2k board-roar board-voip boe-pagesvr boe-processsvr boinc boks boks_clntd bootclient bootserver borland-dsj bpjava-msvc brain bre bridgecontrol brightcore brlp-0 brlp-2 broker_service brvread bsquare-voip btprjctrl btrieve bts-x73 btx bullant-srap busboy bv-agent bvcontrol bv-ds bv-is bv-queryengine bv-smcsrv bvtsonar bwnfs bytex c1222-acse c3 ca-audit-da ca-audit-ds cableport-ax cab-protocol cacp cadis-1 cadis-2 cadkey-licman cadkey-tablet cadlock cadsi-lm cadview-3d caerpc caicci ca-idms caids-sensor cajo-discovery cal call-logging call-sig-trans candp canna can-nds canocentral0 canon-bjnp1 canon-bjnp2 canon-bjnp3 canon-bjnp4 capioverlan capwap-control car CarbonCopy cardax carracho cart-o-rama cas casanswmgmt casp caspssl catchpole cautcpd cba8 cbserver cbt cce3x cce4x ccmail ccmcomm ccm-port ccnx ccp ccproxy-ftp ccproxy-http ccs-software cdbroker cdc cddbp-alt cdfunc cdid cdn cedros_fds celatalk centra cernsysmgmtagt cert-initiator cert-responder cfdptkt cfengine cfs cft-0 cft-5 cft-6 cgms cgn-stat chargen checksum childkey-notif chimera-hwm chip-lm chipper chmd chromagrafx chshell ci3-software-1 ci3-software-2 cichild-lm cichlid cimplex cimtrak cinegrfx-lm ciphire-serv cisco-avp cisco-fna cisco-ipsla ciscopop cisco-sccp cisco-sys cisco-tdp cisco-tna citadel citrix-ica citrixima citriximaclient citynl citysearch cl-1 clariion-evr01 cl-db-attach clearcase client-wakeup cloanto-net-1 clp cluster-disc clvm-cfg cm cma cmip-man cmmdriver cnrprotocol coauthor codaauth2 codasrv codasrv-se CodeMeter cognex-insight coldfusion-auth collaborator com-bardac-dw comcam-io commerce commlinx-avl commonspace commplex-link commtact-http commtact-https comotionback comotionmaster compaqdiag compaq-evm compaq-https compaq-wcp composit-server compressnet compx-lockview comscm con concert condor conf conference conferencetalk config-port confluent connection connect-proxy connect-server connlcli conspiracy contamac_icm contclientms contentserver controlit corba-iiop corba-iiop-ssl corbaloc corelccam corelvideo corerjd cosmocall courier covia cp-cluster cpdi-pidas-cm cpdlc cplscrambler-al cplscrambler-in cplscrambler-lg cppdp cpqrpm-agent cpq-tasksmart cpq-wbem cp-spxdpy cqg-netlan-1 creativepartnr creativeserver crestron-cip crestron-ctp cronus crs cryptoadmin crystalenterprise crystalreports cs-auth-svr csbphonemaster cscp csdm csdmbase csd-mgmt-port csi-sgwp cslistener cs-live csms csms2 csnet-ns cspmlockmgr cspuni csrpc cs-services cst-port csvr-proxy ctf ctp-state ctsd cucme-1 cucme-2 cucme-3 cucme-4 cuelink-disc cuillamartin cumulus cumulus-admin custix cvc cvc_hostd cvd cvmmon cvspserver cxtp cxws cyaserv cybercash cybro-a-bus cycleserv cycleserv2 cymtec-port cypress d2000kernel daap dab-sti-c dandv-tester danf-ak2 dasp datasurfsrv datasurfsrvsec datex-asn davsrcs dayliteserver dayna daytime dbase dbbrowse dbcontrol-oms dbdb dberegister dbisamserver1 dbisamserver2 db-lsp dbm dbreporter dbsa-lm dbstar dc dca dcap d-cinema-rrp dcp dcs dcs-config dcsoftware dctp dcutility d-data d-data-control dddp ddi-tcp-2 ddm-dfm ddm-rdb ddm-ssl ddns-v3 ddrepl ddt de-cache-query decap decauth decbsrv decladebug dec-notes dectalk decvms-sysmgt dei-icda dell-rm-port dellwebadmin-2 delta-mcp denali-server deos derby-repli de-server deslogin deslogind device device2 deviceshare dfn dhcpc dhcp-failover dhcp-failover2 dhcps dhcpv6-client dhcpv6-server diagmond diagnose-proc dialpad-voice1 diameter di-ase dict di-drm dif-port digiman digital-vrc direcpc-video direct directplaysrvr directv-catlg directv-soft directv-web dirgis dis discard disclose distccd distinct distinct32 dist-upgrade dixie dj-ilm dl_agent dlip dls dls-mon dls-monitor dlsrap dlsrpn dlswpn dmaf-caster dmdocbroker dmidi dn6-nlm-aud dn6-smm-red dna-cml dnet-keyproxy dnet-tstproxy dnox dnp dns2go dnsix dns-llq dnx docstor documentum documentum_s domain domaintime doom dossier down downtools-disc dpm dproxy dpsi DragonIDSConsole drip drp ds-admin dsatp dsc dsETOS dsf dsfgw dsmipv6 d-s-n dsp dsp3270 ds-srvr dtag-ste-sb dtk dtn1 dtp dtpt dtspc dtv-chan-req dvapps dvbservdsc dvcprov-port dvl-activemail dvr-esm dvs dwf dwmsgserver dwr dxadmind dx-instrument dxmessagebase1 dxmessagebase2 dxspider dyna-access dynamic3d dynamid ea1 eapsp easy-soft-mux e-builder echo ecolor-imager ecomm edb-server1 e-design-web editbench edm-std-notify edonkey e-dpnet eenet efcp efi-lm efi-mg ehs-ssl ehtp eicon-server eicon-slp eicon-x25 eims-admin eis eisp eklogin ekshell elan elatelink elcn elcsd elektron-admin elfiq-repl eli Elite ellpack elm-momentum elpro_tunnel els elvin_server embl-ndt emb-proj-cmd emcads emce emcrmirccd emfis-cntl emfis-data emperion empire-empuma empowerid emprise-lsc encore encrypted_admin enl enl-name enpc enpp enrp-sctp enrp-sctp-tls ent-engine entexthigh entextlow entextmed entextnetwk entextxid entomb entrust-aaas entrust-aams entrust-ash entrustmanager entrust-sps entrusttime eoss epmd epnsdp ep-nsp epp eppc ep-pcp eq-office-4940 eq-office-4941 equationbuilder erpc erunbook_agent esbroker escp-ip es-elmd esip esl-lm esp esp-encap esp-lm esri_sde esro-emsdp esro-gen essbase essp etebac5 etftp EtherNet/IP-1 EtherNet/IP-2 etlservicemgr ets eudora-set evb-elm event_listener event-port evm ev-services ewall e-woa exasoftport1 exbit-escp excerpt excw exec exlm-agent exp1 exp2 extensis extensisportfolio eyelink eyetv ezmeeting-2 facsys-router fairview famdc farenet fasttrack fatserv fax faxportwinport faxstfx-port fazzt-admin fc-cli fc-faultnotify fcp fcp-addr-srvr2 fcp-srvr-inst1 fcp-udp fc-ser ff-annunc ff-fms ff-lr-port ffserver ff-sm fg-fps fg-sysupdate fhc fhsp filemaker filenet-powsrm filenet-rpc filenet-tms filesphere finger fintrx fiorano-msgsvc firepower firewall1-rdp firstcall42 fis fiveacross fjappmgrbulk fj-hdnet fjhpjp fjicl-tep-a fjinvmgr fjippol-cnsl fjitsuappmgr fjmpjps fjmpss flamenco-proxy flashfiler flashmsg flexlm flex-lm flexlm0 flexlm1 flexlm10 flexlm2 flexlm3 flexlm5 flexlm7 flexlm9 fln-spx florence fmp fmpro-fdal fmpro-v6 fmsas fmsascon fmtp fmwp fnet-remote-ui fodms font-service foresyte-sec fotogcad fpitp fpo-fns frc-hp frc-lp frc-mp freeciv fs-agent ftp ftp-agent ftp-data ftp-proxy ftps ftps-data ftranhc ft-role ftsrv fujitsu-dev fujitsu-dtc fujitsu-dtcns funk-dialout funk-logger funkproxy fuscript fw1-mc-fwmodule fw1-mc-gui fw1-or-bgmp fw1-secureremote fxuptp gacp gadgetgate1way gadgetgate2way galaxy-network galileo galileolog gamegen1 gandalf-lm garcon gat-lmd gcsp gdoi gdomap gdp-port gds-adppiw-db gds_db geneous genie genie-lm geniuslm genrad-mux geognosisman gf ggf-ncp gilatskysurfer ginad git gkrellm globalcatLDAP globalcatLDAPssl global-wlink globe glogger glrpc gmrupdateserv gnunet gnutella gnutella2 goahead-fldup goldleaf-licman go-login gopher gotodevice gpfs gppitnp gprs-cube gprs-sig graphics gridgen-elmd gris groove groove-dpp groupwise gsidcap gsiftp gsigatekeeper gsmp gss-http gss-xlicen gtegsc-lm gtp-control gtrack-server gvcp gv-pf gv-us gwha gw-log h2250-annex-g h225gatedisc h248-binary h2gf-w-2m h323callsigalt h323gatedisc h323gatestat h323hostcallsc H.323/Q.931 hacl-cfg hacl-gs hacl-hb hacl-local hacl-probe hacl-test ha-cluster hagel-dump haipe-otnk halflife hao hap hart-ip hassle hb-engine hcp-wismar hdap hddtemp hde-lcesrvr-2 hdl-srv health-trap hecmtl-db helix hello-port hems here-lm heretic2 hermes hexen2 hfcs hfcs-manager hhb-gateway hiperscan-id hippad hiq hivestor hks-lm hmmp-ind hmmp-op homeportal-web hostname hosts2-ns hotline hotu-chat houdini-lm hp-3000-telnet hp-alarm-mgr hp-clic hp-collector hp-dataprotect hp-hcip hp-hcip-gwy hpidsadmin hp-managed-node hpnpd hppronetman hp-sci hp-server hpss-ndapi hp-status hpstgmgr hpvirtgrp hpvmmagent hpvmmcontrol hpvmmdata hp-webadmin hri-port http http-alt http-mgmt http-proxy http-rpc-epmap https https-alt htuilsrv husky hybrid hybrid-pop hydap hylafax hyper-g hyperip hyperwave-isp i3-sessionmgr iad1 iad2 iad3 iafdbase iafserver ianywhere-dbns iapp iascontrol iascontrol-oms iasd ias-neighbor ias-reg iatp-highpri iberiagames ibm-app ibm-cics ibm-db2 ibm-db2-admin ibm-diradm ibm-dt-2 ibm-mgr ibm-mqisdp ibm-mqseries ibm-pps ibm-res ibm-rsyscon ibm-ssd ibm_wrless_lan icad-el icap icb iccrushmore ice-location icg-swp ici iclcnet-locate iclcnet_svinfo iclpv-dm iclpv-nlc iclpv-nls iclpv-pm iclpv-sas iclpv-sc iclpv-wsm icl-twobase1 icl-twobase2 icl-twobase4 iconp icp icq icslap ida-agent idcp ideafarm-door ideafarm-panic ident identify idfp idmaps idmgratm idp idxp ieee-mih ieee-mms ieee-mms-ssl ies-lm ifor-protocol ifsf-hb-port igcp igi-lm igo-incognito igrs iiimsf iims iiop IIS IISrpc-or-vat imagequery imap imap3 imap4-ssl imaps imgames imoguia-port imqbrokerd imsldoc imsp imtc-mcs imyx incp index-net index-pc-wb indigo-server indura indy i-net-2000-npr infiniswitchcl infolibria infoman informatik-lm informer infoseek infowave ingreslock ingres-net innosys innosys-acl inovaport1 insitu-conf instantia instl_bootc instl_boots intecom-ps1 intecourier integra-sme intellistor-lm intelsync interbase interhdl_elmd intersan interserver intersys-cache interwise int-rcv-cntrl intrinsa intuitive-edge intv invision invokator ioc-sea-lm ionixnetmon iop ipcd ipcd3 ipcore ipcserver ipdcesgbs ipdd ipether232port ipfix ipfixs iphone-sync ipp ip-qsig ipt-anri-anri ipulse-ics ipx iqobject iqserver ique iRAPP irc ircs ircu irdmi irdmi2 irisa iris-beep iris-lwz iris-xpc iris-xpcs irtrans is99c is99s isakmp isbconference1 ischat iscsi isdninfo isg-uda-server isi-gl isis isis-bcast ismaeasdaqtest ismc ismserver isnetserv isode-dua iso-ill iso-ip isoipsigport-1 isoipsigport-2 iso-tp0 iso-tsap iso-tsap-c2 isqlplus isrp-port issa issc iss-console-mgr issd iss-mgmt-ssl iss-realsec iss-realsecure ita-agent itactionserver2 ita-manager item itinternet itm-mcell-s ito-e-gui itu-bicc-stc itv-control iua iuhsctpassoc ivmanager ivsd ivs-video iwec iwg1 i-zipqd izm jaleosnd java-or-OTGfileshare jaxer-manager jcp jdmn-port jediserver jeol-nsddp-3 jeol-nsddp-4 jetdirect jetstream jini-discovery jmact3 jmact5 jmact6 jmb-cds1 jmb-cds2 joaJewelSuite joost jprinter jstel jtag-server kademlia kauth kdm kerberos kerberos-adm kerberos_master kerberos-sec keyserver keyshadow keysrvr kfserver kingdomsonline kingfisher kink kiosk kip kis kjtsiteserver klio klogin kme-trap-port kmscontrol knet-cmp knetd konspire2b kpasswd kpasswd5 kpop krb524 krb5gatekeeper krb_prop krbupdate kryptolan kshell kuang2 kvm-via-ip kx kyoceranetdev l2f L2TP lam la-maint lan900_remote landesk-cba landesk-rc landmarks lanmessenger lanrevagent lanrevserver lanserver lansource lansurveyorxml laplink lazy-ptop lcs-ap ldap ldaps ldapssl ldgateway ldp ldxp lecroy-vicp legent-1 legent-2 leoip lgtomapper liberty-lm licensedaemon link linuxconf linx lipsinc lisp-cons lisp-data lispworks-orb listcrt-port listcrt-port-2 listen livelan ljk-login lkcmserver llmnr llm-pass llsurfup-http llsurfup-https lmdp lmp lms lmsocialserver lm-sserver lnvpoller lnvstatus loadsrv localinfosrvr lockd locus-con locus-map lofr-lm login lonewolf-lm lontalk-norm lorica-in lorica-in-sec lorica-out lot105-ds-upd lotusmtap lotusnotes lrs-paging LSA-or-nterm lsi-raid-mgmt lsnr lsp-ping lstp ltcudp ltp-deepspace lumimgrd lupa lutap lv-ffx m2mservices m2pa m2ua m3ua macon mac-srvr-admin magenta-logic magicnotes mailbox mailbox-lm mailprox mailq maitrd man manage-exec manyone-http mao mapper-mapethd mapper-nodemgr mapper-ws_ethd marcam-lm masqdialer matip-type-a matip-type-b MaxumSP maybe-fw1 maybe-veritas mbg-ctrl mc-client mcer-port mciautoreg mcidas mcns-sec mcns-tel-ret mcreport mcs-messaging mctp mdap-port mdbs_daemon mdc-portmapper mdns mdnsresponder mecomm med-ci media-agent mediabox mediaspace medimageportal med-ovw meetingmaker megaco-h248 megardsvr-port memcachedb menandmice-dns menandmice-lpm menandmice-mon meregister mesavistaco metaconsole meta-corp metagram metasage metasys meter metricadbc metrics-pas mevent mfcobol mfserver mftp mgcp-gateway mib-streaming micom-pfs microcom-sbp micromuse-lm micromuse-ncpw microsan microsoft-ds mikey mimer minecraft minger minilock mini-sql miroconnect mit-dov miteksys-lm mit-ml-dev miva-mqs mkm-discovery mlchat-proxy mloadd mm-admin mmcals mmcc mmpft mnotes mnp-exchange mobileip-agent mobilip-mn mobrien-chat moldflow-lm molly mon mondex monitor monkeycom montage-lm mortgageware MOS-lower mosmig MOS-soap mount mountd movaz-ssc mpc-lifenet mpidcagt mpidcmgr mpm mpm-flags mpm-snd mpp mppolicy-mgr mppolicy-v5 mpshrsv mps-raft mptn mqe-broker mrm msantipiracy ms-cluster-net msdfsr msdp msdtc msdts1 msexch-routing msfrs msfw-control msg-auth msg-icp msgsys mshvlm msl_lmd ms-lsa msmq msmq-mgmt msnp ms-olap1 ms-olap2 ms-olap3 ms-olap4 msolap-ptp2 msp msql ms-rome msrp msrpc msr-plugin-port ms-shuttle ms-sna-base ms-sna-server ms-sql2000 ms-sql-m ms-sql-s ms-streaming ms-v-worlds ms-wbt-server mtl8000-matrix mtn mtp mtport-regist mtqp mtsserver multidropper multiling-http multiplex mumps munin mupdate murray muse musiconline must-backplane must-p2p mvs-capacity mvx-lm mxi mxomss mxxrlogin myblast mylex-mapd mysql mysql-cluster mysql-cm-agent mysql-im mysql-proxy mythtv n1-fwp n1-rmgmt n2h2server n2nremote naap nacagent nacnl na-er-tip namemunge nameserver namp napster nas nati-logos nati-svrloc nati-vi-server nat-pmp nat-t-ike navisphere nav-port nbt-pc nburn_id nbx-cc nbx-dir nbx-ser ncacn-ip-tcp ncadg-ip-udp ncconfig ncd-conf ncd-diag ncd-diag-tcp ncdmirroring ncd-pref ncd-pref-tcp nced ncld ncp ncpm-hip ncr_ccl ncube-lm ndmp ndm-requester ndm-server ndnp ndsauth ndsconnect ndsp ndtp neod1 neod2 nerv nesh-broker nessus nest-protocol net2display netarx netaspi netassistant netattachsdmp netbackup netbill-auth netbill-prod netbios-dgm netbios-ns netbios-ssn netbookmark netboot-pxe netbus netcheque netconf-beep netconfsoapbeep netconfsoaphttp netconf-ssh netcp neteh netgw netinfo netinfo-local netiq-endpt netiq-qcheck netlabs-lm netmagic netmap_lm netml netmo-http netmon netmount netmpi netnews neto-dcs netopia-vo1 netopia-vo2 netopia-vo3 netop-rc netop-school neto-wol-server netrcs netrek netrisk netrix-sftm netrjs-1 netrjs-2 netrjs-3 netrjs-4 netsaint netsc-dev netsc-prod netscript netserialext2 netspeak-cs netstat netuitive netvenuechat netview-aix-1 netview-aix-10 netview-aix-11 netview-aix-12 netview-aix-2 netview-aix-3 netview-aix-4 netview-aix-5 netview-aix-6 netview-aix-7 netview-aix-8 netview-aix-9 netviewdm1 netviewdm2 netviewdm3 netwall netware-csp netware-ip netwatcher-mon networklenss netxms-agent netxms-mgmt netxms-sync newacct newbay-snc-mc newgenpay newlixconfig newlixengine newoak new-rwho news newwavesearch nexgen nexstorindltd nextstep nexus-portal nfa nfs nfsd-keepalive nfsd-status NFS-or-IIS nfsrdma nhci nicelink nicetec-mgmt ni-ftp nim ni-mail nimaux nimhub nimreg nimsh niobserver nip nitrogen ni-visa-remote nkd nlogin nmap nmc-disc nmea-0183 nm-game-admin nmmp nms nmsd nms-dpnss nmsp nmsserver nms_topo_serv nnsp nntp noadmin nokia-ann-ch2 noteit noteshare notify novar-dbase novastorbakcup novation novell-lu6.2 nowcontact npds-tracker nping-echo npmp-gui npmp-local npmp-trap npp nppmp nqs nrcabq-lm nrpe ns nsesrvr nsiiops nsjtp-ctrl nsjtp-data nsp nsrexecd nss nssagentmgr nssocketport nss-routing nsstp nst nsw-fe ntalk ntp nuauth nucleus nucleus-sand nufw nupaper-ss nut nuts_bootp nuts_dem nvcnet nvmsgd nw-license oa-system objcall objective-dbc objectmanager obrpd ocbinder oceansoft-lm ock oc-lm ocs_amu ocs_cmu ocserver octopus odbcpathway odmr odsi oem-agent office-tools oftep-rpc ohimsrv oi-2000 oidsr oirtgsvc olsr omabcastltkm omad oma-dcdocbs oma-mlp oma-mlp-s oma-rlp-s omasgport oma-ulp omfs omginitialrefs omhs omid omnilink-port omnivision omscontact omserv onbase-dds onmux onscreen ontime oob-ws-http opalis-rdv opalis-robot opc-job-start opc-job-track opcua-udp openhpid openmanage openmath opennl-voice openport opentable openvms-sysipc openvpn openwebnet opsec-cvp opsec-ela opsec-lea opsec-sam opsec-ufp opsession-prxy opsession-srvr opswagent optech-port1-lm optilogic optima-vnet optiwave-lm oracle oracleas-https oracle-oms oracle-vp2 ora-lm orasrv orbiter orbix-config orbix-locator orbix-loc-ssl orbplus-iiop os-licman osm-appsrvr ospfd ospf-lite osu-nms osxwebadmin ottp otv ovbus oveadmgr overnet ov-nnm-websrv ovrimosdbman ovsam-d-agent ovsam-mgmt ovtopmd owamp-control p2pcommunity p2pq pacerforum pacmand padl2sim paging-port pago-services1 palace-4 pammratc pammrpc pana panagolin-ident pando-pub paradym-31 paragent park-agent parsec-master partimage passgo passgo-tivoli password-chg patrol-ism patrol-mq-gm patrolview pawserv pcanywhere pcanywheredata pcanywherestat pcduo pcduo-old pciarray pclemultimedia pcm pcmail-srv pc-mta-addrmap pcnfs pctrader pda-gate pdap pdap-np pda-sys pdps pds pdtp peerenabler pegboard pehelp pe-mike peport perfd perf-port personal-link pftp ph pharmasoft pharos philips-vc phonebook photuris phrelay pichat picknfs pim-port pim-rp-disc pip pipes pipe_server piranha1 piranha2 pirp pit-vpn pk pkagent pk-electronics pkix-3-ca-ra pksd pktcable-cops pktcablemmcops playsta2-app playsta2-lob plethora pmdfmgt pmsm-webrctl pn-requester pn-requester2 pns polestar polipo pop2 pop3 pop3pw pop3s popup-reminders portgate-auth postgresql pov-ray powerburst powerchute powerchuteplus poweronnud powerschool ppcontrol ppp ppsms pptconference pptp pra_elmd prat precise-comm presence prgp primaserver printer printer_agent print-srv priority-e-com prismiq-plugin privateark privatechat privatewire priv-dial priv-file priv-mail privoxy priv-print priv-rje priv-term priv-term-l prm-nm prm-nm-np prm-sm prm-sm-np prnrequest prnstatus proaxess profile prolink proofd propel-msgsys proshare1 proshare2 proshareaudio prosharedata prosharenotify prosharerequest prosharevideo prospero proxima-lm proxy-plus prsvp ps-ams pscupd psi-ptt pslserver pssc pt2-discover ptcnameservice ptk-alink pulseaudio puparp purenoise pvuniwien pvxpluscs pwdgen pwgpsi pxc-pin pxc-roid pxc-splr pxc-splr-ft pxc-spvr pxc-spvr-ft pyrrho pythonds q55-pcc qaz qbdb qb-db-server qbikgdp qcp qft qip-audup qip-login qmqp qmvideo qnts-orb qo-secure qotd qpasa-agent qrh qsc qsm-gui qsm-proxy qsm-remote qsnet-assist qsnet-cond qsnet-nucl qsnet-trans qsnet-workst qtms-bootstrap quake quake2 quake3 quakeworld quartus-tcl quasar-server quest-vista quickbooksrds quicktime quotad radacct radan-http radio-bc radius radius-dynauth radmin radmind radsec raid-ac raid-am raid-cc raid-cd raid-cs raid-sf rap rapidmq-reg rapido-ip rap-ip rap-listen rap-service raqmon-pdu ratio-adp ratl raven-rmp razor rbakcup1 rcc-host rcip-itu rcp rcst rcts rda rdrmshc rds rds2 reachout realm-rusd realserver rebol recipe re-conn-proto redstone-cpss reftek registrar relief rellpack re-mail-ck remoteanything remote-as remote-collab remotefs remote-kis remote-winsock rendezvous repcmd repliweb repscmd repsvc resacommunity resvc retrospect RETS-or-BackupExec rfa rfb rfe rfio rfmp rfx-lm rgtp rhp-iibp rib-slm ricardo-lm ridgeway2 rightbrain rimsl ripd ripng ris ris-cm rje rkinit rlm rlm-admin rlp rlzdbase rmc rmiactivation rmiaux rmiregistry rmonitor rmonitor_secure rmpp rmt rna-lm rndc robcad-lm robix roboeda roboer rockwell-csp1 rockwell-csp2 roketz rootd route routematch rpasswd rpc2portmap rpcbind rpi rplay rrac rrh rrifmm rrilwm rrimwm rrp rsap rsf-1 rsftp rsh-spx rsip rsom rsqlserver rsvd rsvp-encap-2 rsvp_tunnel rsync rtcm-sc104 rtelnet rtip rtmp rtps-dd-mt rtps-discovery rtraceroute rtsclient rtsp rtsps rtsserv rusb-sys-port rushd rwhois rww rxapi rxe rxmon



syn region nmapProto start="s1-control sabarsd sac sacred sae-urn safetynetp saft sage-best-com2 sagectlpanel sah-lm samba-swat samsung-unidex sanavigator sane-port sanity santools sapcomm sapeps saphostctrl saphostctrls saposs saprouter sapv1 saris sas-1 sas-2 sas-3 sasg sasggprs sasp satvid-datalnk savant sbcap sbi-agent sbl sbook scan-change scanstat-1 sccip-media scc-security sceanics scientia-sdb scientia-ssdb sco-dtmgr scohelp scoi2odialog sco-inetmgr scol scoremgr sco-sysmgr scotty-ft sco-websrvrmg3 sco-websrvrmgr scp scp-config scpi-raw scrabble screencast scriptview scservp scte30 sctp-tunneling scx-proxy sd sdadmind sddp sde-discovery sdfunc sdl-ets sdlog sdnskmp sdo-ssh sdp-portmapper sdproxy sdr sds sds-admin sdsc-lm sdserv sdt-lmd sdxauthd seagull-ais seagulllms search search-agent seclayer-tcp sec-t4net-srv secure-aux-bus secure-cfg-svr secureidprop securenetpro-sensor securid semantix send senomix01 sentinel-ent sentinel-lm sentinelsrm seosload serialgateway serialnumberd servergraph serverview-as serverview-asn serverview-icc servexec servicemeter servicetags servistaitsm servserv servstat set sflm sfs-config sfs-smp-net sftp sftsrv sgcp sge_qmaster sgi-dgl sgi-esphttp sgi-eventmond sgmp sgmp-traps sgsap shadowserver shareapp shell shiva_confsrvr shivadiscovery shivahose shivasound shockwave shockwave2 shrinkwrap siam siebel-ns sieve sift-uft sightline sigma-port siipat silc silhouette silkp3 silverpeakcomm silverplatter simba-cs simbaexpress simbaservices simco sim-control simp-all simplifymedia sip sip-tls sitaradir sitaraserver sitewatch sixnetudr sixtrak sj3 skkserv skronk skytelnet slc-systemlog slim-devices slinkysearch slm-api slnp slp slslavemon slush smakynet smap smart-lm smartsdp smauth-port smc-http smc-https smile smip-agent smntubootstrap sm-pas-3 smpnameres smpte smsd smsp sms-rcinfo sms-remctrl sms-xfer smtp smtps smux smwan snagas snap snare s-net snet-sensor-mgmt snews snifferserver snmp snmpdtls-trap snmp-tcp-port snmptrap snpp sns-channels sns_credit sns-dispatcher sntp-heartbeat soagateway soap-beep soap-http socalia socks softaudit softcm softdataphone softpc softrack-meter solid-mux sometimes-rpc1 sometimes-rpc10 sometimes-rpc11 sometimes-rpc12 sometimes-rpc13 sometimes-rpc14 sometimes-rpc15 sometimes-rpc16 sometimes-rpc17 sometimes-rpc18 sometimes-rpc19 sometimes-rpc2 sometimes-rpc20 sometimes-rpc21 sometimes-rpc22 sometimes-rpc23 sometimes-rpc24 sometimes-rpc25 sometimes-rpc26 sometimes-rpc27 sometimes-rpc28 sometimes-rpc3 sometimes-rpc4 sometimes-rpc5 sometimes-rpc6 sometimes-rpc7 sometimes-rpc8 sometimes-rpc9 sonar sonardata soniqsync sophia-lm sophos sops sor-update spamassassin spc spcsdlobby spdp spectraport splitlock spmp spramsd spsc spss spt-automation spw-dialer spw-dnspreload sqdr sqlexec sqlexec-ssl sqlnet sql-net sqlserv sqlsrv squid-htcp squid-http squid-ipc squid-snmp src srmp srp-feedback srssend ss7ns sscan ssdispatch sse-app-config ssh sshell ssh-mgmt sslp ssmc sso-control sso-service ssp-client ssserver ssslic-mgr ssslog-mgr sstats stanag-5066 starfish starquiz-port starschool startron stat-cc stat-scanner statsci1-lm statsci2-lm statsrv statusd stel stgxfws stmf stm_pproc stone-design-1 streetperfect street-stream stt stun-p1 stun-p2 stun-p3 stun-port stx sua submission submit submitserver subntbcst_tftp subseven suitcase suitjd su-mit-tg sun-answerbook sun-as-iiops-ca sun-as-jmxrmi sun-as-jpda suncacao-jmxmp sunclustermgr sun-dr sun-manageconsole sun-sea-port sun-sr-jmx sun-user-https sunwebadmin supdup supermon supfiledbg supfilesrv support surf surfcontrolcpa surfpass sur-meas surveyinst svn svnetworks svrloc swdtp-sv sweetware-apps swift-rvf swldy-sias swx swxadmin sxmp syam-webserver sybase sybaseanywhere sybasedbsynch sygatefw symantec-av symantec-sfdb symb-sb-port symplex synapse synchronet-db synel-data synoptics-trap synotics-broker synotics-relay sype-transport syscomlan sysinfo-sp syslog syslog-conn sysopt systat" end=" "
" t2-brm tabula tacacs tacacs-ds tacnews tacticalauth taep-as-svc tag-ups-1 talarian-mcast1 talarian-mcast2 talarian-mcast3 taligent-lm talk talon-engine tam tambora tams tapestry tapeware targus-getdata targus-getdata1 targus-getdata2 taurus-wh tbrpf tcc-http tcoflashagent tcoregagent tcp-id-port tcpmux tcpnethaspsrv tdaccess tdmoip td-postman tdp-suite td-replica td-service teamcoherence teedtap telefinder telelpathattack telelpathstart teleniumdaemon telesis-licman tell telnet telnets tempo tenebris_nts tenfold teradataordbms teredo terminaldb texar tftp tgp thrp ticf-1 ticf-2 tick-port tig timbuktu timbuktu-srv1 timbuktu-srv2 timbuktu-srv3 timbuktu-srv4 time timed timeflies tinc tinyfw tip2 tip-app-server tivoconnect tl1-raw-ssl tlisrv tmi tmo-icon-sync tmosms0 tmosms1 tnETOS tnp tnp1-port tns-cml tn-timing tn-tl-fd1 tn-tl-fd2 tn-tl-r1 tn-tl-w2 tolteces topflow topflow-ssl topovista-data topx tor-control tor-orport tor-socks tor-trans touchnetplus tpcsrvr tpdu tpip tpmd tqdata tram trap trap-daemon travsoft-ipx-t tributary trident-data trim Trinoo_Bcast Trinoo_Master Trinoo_Register triomotion tripwire trivnet1 trivnet2 troff tr-rsrb-p1 tr-rsrb-p2 tr-rsrb-p3 tr-rsrb-port trusted-web tsa tscchat tsdos390 tserver tsilb tsp tsrmagt ttntspauto ttyinfo tungsten-https tunnel tvbus tvpm twamp-control twcss twrpc uaac uadtc uaiact uarps ubroker udrawgraph udt_os ufmp ufsd uis ulistserv ulp ulpnet ultraseek-http ultrex umeter unbind-cluster unet unicall unidata-ldm unieng unify unikeypro unisys-eportal unisys-lm unitary univ-appserver unix-status unizensus unknown unot upnotifyp upnp ups ups-engine ups-onlinet urm user-manager us-gv us-srv utcd utime utmpcd utmpsd uucp uucp-path uucp-rlogin uuidgen v5ua vacdsm-sws valisys-lm varadero-1 varadero-2 vat vat-control vatp vce vchat vcom-tunnel vdmplay vemmi venus venus-se veracity vergencecm veritas_pbx veritas-ucl veritas-vis2 vettcp vfo via-ftp vid video-activmail videotex videte-cipc vieo-fe vinainstall virprot-lm virtual-places virtualtape virtualuser visionpyramid visitview vistium-share vitalanalysis vlsi-lm vmnet vmodem vmpwscs vmrdp vmsvc vmsvc-2 vmware-auth vmware-fdm vnas vnc vnc-1 vnc-2 vnc-3 vnc-http vnc-http-1 vnc-http-2 vnc-http-3 vnetd vnsstr vnwk-prapi vocaltec-admin vocaltec-hos vocaltec-wconf vp2p vpac vpad vpjp vpnz vpp vpps-qua vpps-via vpsipport vpvc vpvd vqp vrace vrml-multi-use vrt vrts-at-port vrts-ipcserver vrtstrapserver vrxpservman vsamredirector vscp vsiadmin vsinet vsixml vslmp vspread vs-server vstat vtsas vulture vvr-data vxcrnbuport vytalvaultbrtp wafs wag-service wanscaler wap-push wap-push-http wap-push-https wap-vcal-s wap-vcard-s wap-wsp wap-wsp-s warehouse-sss warmspotMgmt waste watchdog-nt watchme-7272 watcom-sql watershed-lm watilapp wbem-http wbem-https wbem-rmi wdbrpc web2host weblogin webmail-2 webobjects webster westec-connect westell-stats wfremotertm wherehoo whisker who whoami whois whosells whosockami WibuKey wincim windb winddlb windows-icfw winjaserver winpcs winpharaoh winpoplanmess win-rpc wins winshadow wip-port wizard wkars wkstn-mon wlanauth wmc-log-svc wmedistribution wmereceiving wmereporting wms wnn6 wnn6_DS work-sol world-lm worldscores worldwire wormux wpages wpgs writesrv wrs_registry wsdapi ws-discovery wsman wsmans wsmlb wso2esb-console wssauthsvc www-dev wysdmc x11 X11 X11:1 X11:2 X11:3 X11:4 X11:5 X11:59 X11:6 X11:7 X11:8 X11:9 x25-svc-port x2-control x9-icue xact-backup xaudio xdmcp xdsxdm xecp-node xfer xfr xgrid xic xiip xingcsm xingmpeg xinuexpansion1 xinuexpansion2 xinuexpansion3 xinuexpansion4 xinupageserver xlog xmail-ctrl xmlink-connect xmlrpc-beep xmltec-xmlmail xmms2 xmpp xmpp-bosh xmpp-client xmpp-server xmquery xnm-clear-text xnmp xnm-ssl xns-auth xns-ch xns-courier xns-mail xns-time xpanel xprint-server xprtld xribs xrl xtell xtreamx xtreelic xtrm xvttp xyplex-mux yak-chat yo-main z39.50 zannet zebra zebrasrv zenginkyo-1 zenginkyo-2 zen-pawn zented zep zephyr-clt zephyr-hm zephyr-srv zeroconf zeus-admin zfirm-shiprush3 zicom zigbee-ip zigbee-ips zincite-a zion-lm zserv"

" This isn't an exhaustive list, it's funny/odd/retro devices which stand out
" because they are funny/odd/retro. Remember, this is only devices which flag
" up specially in bold white on red. 'Normal' fingerprints still match as usual

" This hightlights the 'OS details:' line, after the : I've tried to keep one
" per line so it makes readability/updates easier, except on OS levels.

syn region nmapFunnyOS start="2N Helios IP VoIP doorbell" end=".*"
syn region nmapFunnyOS start="3M Filtrete 3M-50 thermostat" end=".*"
syn region nmapFunnyOS start="s 4G Systems XSBoxGO+ WAP" end=".*"
syn region nmapFunnyOS start="s Acer S5200 projector" end=".*"
"s AirMagnet SmartEdge wireless sensor; or Foscam FI8904W, FI8910W, or FI8918W, or Instar IN-3010 surveillance camera
syn region nmapFunnyOS start="AmigaOS 3\.[0-9]" end=".*"
"s Anue X/GEM ethernet network simulator
syn region nmapFunnyOS Start="Apple A/UX" end="3.0.1 - 3.1.1 SVR2"
"s Audio receiver: Bowers & Wilkins Zeppelin Air, Denon AVR-1900-series, Marantz NR1602, or Pioneer VSX-921
"s AVtech Room Alert 26W environmental monitor
"s AXIS 70U Network Document Server
"s Barrelfish before release2011-09-02
"s Bay Networks Annex Ethernet-to-serial bridge or Xerox DocuPrint N32 printer
"s BeaconMedaes TotalAlert medical gas alarm
"s Belkin OmniView KVM switch or SMA Sunny WebBox solar panel monitor
"s Bluebird SuperDOS
"s Bluebottle OS
"s Bosch Divar security system
"s Boundless Technologies NetTerminal text terminal
"s British Gas GS-Z3 data logger
"s BT Vision+ set-top box (Windows CE 5.0.1400)
"s Burny CNC controller (Microsoft Windows XP Embedded)
"s cab A4+/300 label printer
"s CAEN SY2527 high voltage power supply
"s Caldera Open Unix 7.1.0
"s Chip PC XtremePC thin client
"s CipherLab 5100 time and attendance terminal
"s Tektronix TDS3034B oscilloscope
"s CMI Genus NEMA terminal
"s Cobalt Qube 1 2700WG (Linux 2.0.34)
"s Cognex DataMan 200 ID reader (lwIP TCP/IP stack)
"s Comau C4G robot control unit
"s Cray UNICOS/mk 2.0.5.60
"s Crestron AV2 or CP2E automation system or TPS-6x touchpanel (2-Series), or Dedicated Micros Digital Sprite 2 DVR
"s Crestron CNMSX-AV control and automation system
"s Crestron MC2E, MP2E, PRO2, or QM-RMC control and automation system, or HP StorageWorks MSL4048 tape library
"s Datalogic Kyman barcode scanner (Windows CE 5.0)
"s Data ONTAP 6.3.2
"s DEC TOPS-20
"s Digi NET+OS 7
"s DMP XR500 remote alarm monitor
"s elmeg T240 or T444 PABX (Linux 2.0.38)
"s Encore 3G or EnGenius ESR-9752 WAP
"s Enerdis Enerium 200 energy monitoring device or Mitsubishi XD1000 projector
"s FreeBSD 2.2.8-STABLE - 2.2.9 (x86)
"s Fuji DryPix medical imager (Microsoft Windows XP Embedded)
"s Fujitsu Siemens BS2000/OSD
"s Fujitsu Siemens Pocket LOOX 750 GPS device (Windows Mobile 5)
"s GNU Hurd 0.3
syn region nmapFunnyOS start="Google Mini search appliance" end=".%"
"s GoPro Wifi-Bacpac camera
"s Green Hills Probe hardware debugger
"s Green Hills RTOS
"s H3C Comware 5.20
"s HP MPE/iX 7.5
"s HP NonStop OS
"s HP NonStop OS H06.19.00
"s Symmetricon NTS-150 time server
"s HW group HWg-STE Ethernet thermometer
"s HW group Poseidon 3265 Ethernet thermometer
"s IBM i 7.1
"s IBM OS/2 Warp 2.0
syn region nmapFunnyOS start="IBM z/OS" end=".$"
"s Inova OnTime Clock Version 1.2.P
"s ipTIME PRO 54G WAP
"s iPXE 1.0.0+
"s ITW WeatherGoose II environmental monitor
"s Kapsch electronic toll collection system
"s Kartina SIG 220 set-top box
"s Kongsberg Seatex BS410 AIS base station (maritime communication component)
"s Koukaam NETIO-230A power control device
"s KW-Software ProConOS
"s LaCrosse WA-1030U weather forecaster
"s Liebert Nfinity UPS
"s Linksys WET54G wireless bridge or Red-M Communications Red-Alert PRO wireless activity detector
"s Linux 1.0.9
"s Linux 2.4.21 (SuSE 9.1)
"s Luminary Micro ARM Evaluation Kit
syn region nmapFunnyOS start="lwIP 1.[1,3,4].0" end="lightweight TCP/IP stack"
"s Lyngsoe Systems RFID reader
"s Metrix Scopix III oscilloscope
"s Microsoft Network Client 3.0 for MS-DOS
syn region nmapFunnyOS start="Microsoft Windows [3\.1\&for]" end=".$"
syn region nmapFunnyOS start="Microsoft Windows Fundamentals for Legacy PCs" end="(XP Embedded derivative)"
syn region nmapFunnyOS start="Microsoft Windows Longhorn" end=".$"
syn region nmapFunnyOS start="Microsoft Windows NT 3" end=".$"
"s Microsoft Windows XP SP3 (MicroXP)
"s Microsoft Xbox game console (modified, running XboxMediaCenter)
"s Microsoft Zune audio player (firmware 3.1)
syn region nmapFunnyOS start="Minix" end=".$"
"s Modtronix single-board computer SBC65EC v3.03
"s Motorola System V/88 Unix R4.0
"s National Instruments CompactRIO automation controller
"s nCircle IP360 security appliance
syn region nmapFunnyOS start="NCR 5676 or 5688 automated teller machine" end=".$"
syn region nmapFunnyOS start="Ness M1-XEP home automation interface" end=".$"
"s NetBurner MOD5270 Ethernet module or Zebra Z4MPlus label printer
"s NetOptics iBypass switch
" syn region nmapFunnyOS start="NeXT [NEXT|OPEN]STEP" end=".*" <-- non working
"s NeXT NEXTSTEP 3.3 (patch level 3, m68k) or OPENSTEP 4.2
"s NeXT OPENSTEP 4.2

syn region nmapFunnyOS start="Nintendo" end="game console"
syn region nmapFunnyOS start="Novatel MiFi 2200 3G WAP or iDirect Evolution X1 satellite" end="router"
syn region nmapFunnyOS start="Novell NetWare" end="3.12"
syn region nmapFunnyOS start="NTI Enviromux-Mini environmental monitoring" end="appliance"
syn region nmapFunnyOS start="Nut/OS 4.3.2 beta" end="(ARM)"
syn region nmapFunnyOS start="On Time RTOS-32" end="3.0"
syn region nmapFunnyOS start="Priva building management" end=" system"
syn region nmapFunnyOS start="Revo Blik Wi-Fi Internet" end=" radio"
syn region nmapFunnyOS start="RF Code RFID reader" end=".*"
syn region nmapFunnyOS start="RF-Space SDR-IP software" end="radio"
syn region nmapFunnyOS start="Rio Karma media player" end=".*"
syn region nmapFunnyOS start="RISCOS Ltd RISC OS 4.39" end=".*"
syn region nmapFunnyOS start="RISCOS Ltd RISC OS 6.20" end=".*"
syn region nmapFunnyOS start="Riverbed RiOS" end=".*"
syn region nmapFunnyOS start="RSA SecurID authentication appliance" end=".*"
syn region nmapFunnyOS start="RuggedCom RSG2288 switch (ROS 3.8.2 - 3.11)" end=".*"
syn region nmapFunnyOS start="Sagem My du@l radio 700 Internet radio" end=".*"
"s Samsung Bada 1.2
"s Samsung LE32B651 TV
"s Satel ETHM-2 intruder alarm
"s Schneider Electric TSX ETY programmable logic controller
"s Schrack electric meter
"s Schweitzer Engineering SEL-2701 Ethernet processor
"s Secure Computing SecureOS 7.0.0.04
"s Sensatronics E4 temperature monitor
"s Sensatronics EM1 environmental monitor
"s Sequent DYNIX (BSD-based Unix)
syn region nmapFunnyOS start="Sony BDP-S370 or BDP-S570 Blu-ray player" end=".*"
syn region nmapFunnyOS start="Sony BDV-[E,T][5,9]7" end="television"
syn region nmapFunnyOS start="Sony Bravia KDL-[3,4][0,2,6][HS,V,W,X]" end="0 TV"
syn region nmapFunnyOS start="Sony CMT-MX700Ni audio player" end=".*"
syn region nmapFunnyOS start="Sony PlayStation 2" end=".$"
syn region nmapFunnyOS start="Sony PlayStation 3" end=".$"
syn region nmapFunnyOS start="Sony PSP game console (modified, running Custom Firmware 3.90 - 5.50)" end=".*"
syn region nmapFunnyOS start="Sony SMP-N200 media player" end=".*"
syn region nmapFunnyOS start="Star Micronics TSP100 receipt printer" end=".*"
syn region nmapFunnyOS start="Star Track SRT2014HD satellite receiver (Linux 2.6)" end=".*"
syn region nmapFunnyOS start="Stonewater Control Systems environmental monitoring appliance" end=".*"
syn region nmapFunnyOS start="Sun Solaris 2.5.1 (SPARC)" end=".*"
syn region nmapFunnyOS start="Sun Solaris 2.6" end=".*"
syn region nmapFunnyOS start="Tahoe 8216 power management system" end=".*"
syn region nmapFunnyOS start="Vantage HD7100S satellite receiver" end=".*"
syn region nmapFunnyOS start="Western Digital WD TV media player" end=".*"
syn region nmapFunnyOS start="WowWee Rovio mobile webcam" end=".*"
syn region nmapFunnyOS start="W&T Web-IO Thermometer model 57101" end=".*"
syn region nmapFunnyOS start="W&T Web-Thermograph NTC" end=".$"
syn region nmapFunnyOS start="W&T Web-Thermo-Hygrobarograph firmware 1.59 - 1.71" end=".*"
syn region nmapFunnyOS start="Wyse C10LE, S10, SX0, 1200LE, or Xenith terminal (ThinOS 6.5)" end=".*"
syn region nmapFunnyOS start="Wyse Cx0 terminal (ThinOS)" end=".*"
syn region nmapFunnyOS start="Wyse S50 thin client (Linux 2.6)" end=".*"
syn region nmapFunnyOS start="Wyse ThinOS 5.2" end=".*"
syn region nmapFunnyOS start="Wyse V10L or 1200LE thin client" end=".*"

if version >= 508 || !exists("did_nmap_syn_inits")
if version <= 508 
    let did_w3af_syn_inits = 1 
    command -nargs=+ HiLink hi link <args>
else
    command -nargs=+ HiLink hi def link <args>
endif

" The default methods for highlighting.  Can be overridden later

" Valid colourse: Black DarkBlue DarkGreen DarkCyan DarkRed DarkMagenta
" Brown DarkYellow LightGray, LightGrey, Gray, Grey DarkGray DarkGrey
" Blue, LightBlue Green LightGreen Cyan LightCyan Red LightRed Magenta
" LightMagenta Yellow LightYellow White

hi nmapBanner ctermfg=red cterm=bold guifg=red
hi nmapNSE ctermfg=red guifg=red
hi nmapStatement ctermfg=Magenta cterm=bold guifg=Magenta
hi nmapPortStatusGood ctermfg=Green cterm=bold guifg=DarkGreen
hi nmapPortStatusBad ctermfg=Red guifg=Red
HiLink nmapComment Comment
hi nmapReport ctermfg=DarkMagenta cterm=bold guifg=DarkMagenta
hi nmapURL ctermfg=LightBlue guifg=LightBlue
hi nmapOSDetection ctermfg=LightBlue cterm=bold guifg=LightBlue
hi nmapDone ctermfg=LightGreen cterm=bold guifg=DarkGreen

hi nmapPort ctermfg=LightCyan guifg=LightCyan

hi nmapProto ctermfg=LightMagenta guifg=LightMagenta
hi nmapIP ctermfg=blue guifg=blue
HiLink nmapHostName Underlined
hi nmapService ctermfg=LightBlue guifg=DarkBlue

hi nmapMACAddress ctermfg=LightGreen guifg=LightGreen

hi nmapTimePeriod ctermfg=White cterm=bold guifg=White
hi nmapScanTime ctermfg=White cterm=bold guifg=White
hi nmapDate ctermfg=White cterm=bold guifg=White

hi nmapTCPPrediction ctermfg=LightMagenta guifg=LightMagenta

hi nmapDeviceType ctermfg=Magenta guifg=Magenta
hi nmapDeviceTypeLine ctermfg=Red guifg=Red

hi nmapErrorWarning ctermfg=DarkRed guifg=DarkRed

hi nmapOSDetails ctermfg=Yellow cterm=bold guifg=Yellow
hi nmapOSRunning ctermfg=DarkYellow guifg=DarkYellow
hi nmapFunnyOS ctermfg=White ctermbg=Red cterm=bold guifg=White guibg=Red
"This one is needed to get them to be different shades of yellow
HiLink nmapOSCPE Statement
hi nmapServiceInfo ctermfg=white guifg=white

hi nmapSubmit ctermfg=LightGreen guifg=LightGreen

HiLink nmapKnightmareComment Todo
hi nmapScriptOutput ctermfg=white ctermbg=Blue

delcommand HiLink
endif

let b:current_syntax = 'nmap'                         
