# kae.py
#
# Generated on Sun Dec 30 17:39:53 +0000 2007


# AEDataModel.h

typeBoolean = b'bool'
typeChar = b'TEXT'

typeStyledUnicodeText = b'sutx'
typeEncodedString = b'encs'
typeUnicodeText = b'utxt'
typeCString = b'cstr'
typePString = b'pstr'

typeUTF16ExternalRepresentation = b'ut16'
typeUTF8Text = b'utf8'

typeSInt16 = b'shor'
typeUInt16 = b'ushr'
typeSInt32 = b'long'
typeUInt32 = b'magn'
typeSInt64 = b'comp'
typeUInt64 = b'ucom'
typeIEEE32BitFloatingPoint = b'sing'
typeIEEE64BitFloatingPoint = b'doub'
type128BitFloatingPoint = b'ldbl'
typeDecimalStruct = b'decm'

typeSMInt = typeSInt16
typeShortInteger = typeSInt16
typeInteger = typeSInt32
typeLongInteger = typeSInt32
typeMagnitude = typeUInt32
typeComp = typeSInt64
typeSMFloat = typeIEEE32BitFloatingPoint
typeShortFloat = typeIEEE32BitFloatingPoint
typeFloat = typeIEEE64BitFloatingPoint
typeLongFloat = typeIEEE64BitFloatingPoint
typeExtended = b'exte'

typeAEList = b'list'
typeAERecord = b'reco'
typeAppleEvent = b'aevt'
typeEventRecord = b'evrc'
typeTrue = b'true'
typeFalse = b'fals'
typeAlias = b'alis'
typeEnumerated = b'enum'
typeType = b'type'
typeAppParameters = b'appa'
typeProperty = b'prop'
typeFSRef = b'fsrf'
typeFileURL = b'furl'
typeKeyword = b'keyw'
typeSectionH = b'sect'
typeWildCard = b'****'
typeApplSignature = b'sign'
typeQDRectangle = b'qdrt'
typeFixed = b'fixd'
typeProcessSerialNumber = b'psn '
typeApplicationURL = b'aprl'
typeNull = b'null'

typeFSS = b'fss '

typeCFAttributedStringRef = b'cfas'
typeCFMutableAttributedStringRef = b'cfaa'
typeCFStringRef = b'cfst'
typeCFMutableStringRef = b'cfms'
typeCFArrayRef = b'cfar'
typeCFMutableArrayRef = b'cfma'
typeCFDictionaryRef = b'cfdc'
typeCFMutableDictionaryRef = b'cfmd'
typeCFNumberRef = b'cfnb'
typeCFBooleanRef = b'cftf'
typeCFTypeRef = b'cfty'

typeKernelProcessID = b'kpid'
typeMachPort = b'port'

typeApplicationBundleID = b'bund'

keyTransactionIDAttr = b'tran'
keyReturnIDAttr = b'rtid'
keyEventClassAttr = b'evcl'
keyEventIDAttr = b'evid'
keyAddressAttr = b'addr'
keyOptionalKeywordAttr = b'optk'
keyTimeoutAttr = b'timo'
keyInteractLevelAttr = b'inte'
keyEventSourceAttr = b'esrc'
keyMissedKeywordAttr = b'miss'
keyOriginalAddressAttr = b'from'
keyAcceptTimeoutAttr = b'actm'
keyReplyRequestedAttr = b'repq'

kAEDebugPOSTHeader = (1 << 0)
kAEDebugReplyHeader = (1 << 1)
kAEDebugXMLRequest = (1 << 2)
kAEDebugXMLResponse = (1 << 3)
kAEDebugXMLDebugAll = 0xFFFFFFFF

kSOAP1999Schema = b'ss99'
kSOAP2001Schema = b'ss01'

keyUserNameAttr = b'unam'
keyUserPasswordAttr = b'pass'
keyDisableAuthenticationAttr = b'auth'
keyXMLDebuggingAttr = b'xdbg'
kAERPCClass = b'rpc '
kAEXMLRPCScheme = b'RPC2'
kAESOAPScheme = b'SOAP'
kAESharedScriptHandler = b'wscp'
keyRPCMethodName = b'meth'
keyRPCMethodParam = b'parm'
keyRPCMethodParamOrder = b'/ord'
keyAEPOSTHeaderData = b'phed'
keyAEReplyHeaderData = b'rhed'
keyAEXMLRequestData = b'xreq'
keyAEXMLReplyData = b'xrep'
keyAdditionalHTTPHeaders = b'ahed'
keySOAPAction = b'sact'
keySOAPMethodNameSpace = b'mspc'
keySOAPMethodNameSpaceURI = b'mspu'
keySOAPSchemaVersion = b'ssch'

keySOAPStructureMetaData = b'/smd'
keySOAPSMDNamespace = b'ssns'
keySOAPSMDNamespaceURI = b'ssnu'
keySOAPSMDType = b'sstp'

kAEUseHTTPProxyAttr = b'xupr'
kAEHTTPProxyPortAttr = b'xhtp'
kAEHTTPProxyHostAttr = b'xhth'

kAESocks4Protocol = 4
kAESocks5Protocol = 5

kAEUseSocksAttr = b'xscs'
kAESocksProxyAttr = b'xsok'
kAESocksHostAttr = b'xshs'
kAESocksPortAttr = b'xshp'
kAESocksUserAttr = b'xshu'
kAESocksPasswordAttr = b'xshw'

kAEDescListFactorNone = 0
kAEDescListFactorType = 4
kAEDescListFactorTypeAndSize = 8

kAutoGenerateReturnID = -1
kAnyTransactionID = 0

kAEDataArray = 0
kAEPackedArray = 1
kAEDescArray = 3
kAEKeyDescArray = 4

kAEHandleArray = 2

kAENormalPriority = 0x00000000
kAEHighPriority = 0x00000001

kAENoReply = 0x00000001
kAEQueueReply = 0x00000002
kAEWaitReply = 0x00000003
kAEDontReconnect = 0x00000080
kAEWantReceipt = 0x00000200
kAENeverInteract = 0x00000010
kAECanInteract = 0x00000020
kAEAlwaysInteract = 0x00000030
kAECanSwitchLayer = 0x00000040
kAEDontRecord = 0x00001000
kAEDontExecute = 0x00002000
kAEProcessNonReplyEvents = 0x00008000

kAEDefaultTimeout = -1
kNoTimeOut = -2



# AEHelpers.h

aeBuildSyntaxNoErr = 0
aeBuildSyntaxBadToken = 1
aeBuildSyntaxBadEOF = 2
aeBuildSyntaxNoEOF = 3
aeBuildSyntaxBadNegative = 4
aeBuildSyntaxMissingQuote = 5
aeBuildSyntaxBadHex = 6
aeBuildSyntaxOddHex = 7
aeBuildSyntaxNoCloseHex = 8
aeBuildSyntaxUncoercedHex = 9
aeBuildSyntaxNoCloseString = 10
aeBuildSyntaxBadDesc = 11
aeBuildSyntaxBadData = 12
aeBuildSyntaxNoCloseParen = 13
aeBuildSyntaxNoCloseBracket = 14
aeBuildSyntaxNoCloseBrace = 15
aeBuildSyntaxNoKey = 16
aeBuildSyntaxNoColon = 17
aeBuildSyntaxCoercedList = 18
aeBuildSyntaxUncoercedDoubleAt = 19



# AEMach.h

keyReplyPortAttr = b'repp'

typeReplyPortAttr = keyReplyPortAttr



# AEObjects.h

kAEAND = b'AND '
kAEOR = b'OR  '
kAENOT = b'NOT '
kAEFirst = b'firs'
kAELast = b'last'
kAEMiddle = b'midd'
kAEAny = b'any '
kAEAll = b'all '
kAENext = b'next'
kAEPrevious = b'prev'
keyAECompOperator = b'relo'
keyAELogicalTerms = b'term'
keyAELogicalOperator = b'logc'
keyAEObject1 = b'obj1'
keyAEObject2 = b'obj2'
keyAEDesiredClass = b'want'
keyAEContainer = b'from'
keyAEKeyForm = b'form'
keyAEKeyData = b'seld'

keyAERangeStart = b'star'
keyAERangeStop = b'stop'
keyDisposeTokenProc = b'xtok'
keyAECompareProc = b'cmpr'
keyAECountProc = b'cont'
keyAEMarkTokenProc = b'mkid'
keyAEMarkProc = b'mark'
keyAEAdjustMarksProc = b'adjm'
keyAEGetErrDescProc = b'indc'

formAbsolutePosition = b'indx'
formRelativePosition = b'rele'
formTest = b'test'
formRange = b'rang'
formPropertyID = b'prop'
formName = b'name'
formUniqueID = b'ID  '
typeObjectSpecifier = b'obj '
typeObjectBeingExamined = b'exmn'
typeCurrentContainer = b'ccnt'
typeToken = b'toke'
typeRelativeDescriptor = b'rel '
typeAbsoluteOrdinal = b'abso'
typeIndexDescriptor = b'inde'
typeRangeDescriptor = b'rang'
typeLogicalDescriptor = b'logi'
typeCompDescriptor = b'cmpd'
typeOSLTokenList = b'ostl'

kAEIDoMinimum = 0x0000
kAEIDoWhose = 0x0001
kAEIDoMarking = 0x0004
kAEPassSubDescs = 0x0008
kAEResolveNestedLists = 0x0010
kAEHandleSimpleRanges = 0x0020
kAEUseRelativeIterators = 0x0040

typeWhoseDescriptor = b'whos'
formWhose = b'whos'
typeWhoseRange = b'wrng'
keyAEWhoseRangeStart = b'wstr'
keyAEWhoseRangeStop = b'wstp'
keyAEIndex = b'kidx'
keyAETest = b'ktst'



# AEPackObject.h



# AERegistry.h

cAEList = b'list'
cApplication = b'capp'
cArc = b'carc'
cBoolean = b'bool'
cCell = b'ccel'
cChar = b'cha '
cColorTable = b'clrt'
cColumn = b'ccol'
cDocument = b'docu'
cDrawingArea = b'cdrw'
cEnumeration = b'enum'
cFile = b'file'
cFixed = b'fixd'
cFixedPoint = b'fpnt'
cFixedRectangle = b'frct'
cGraphicLine = b'glin'
cGraphicObject = b'cgob'
cGraphicShape = b'cgsh'
cGraphicText = b'cgtx'
cGroupedGraphic = b'cpic'

cInsertionLoc = b'insl'
cInsertionPoint = b'cins'
cIntlText = b'itxt'
cIntlWritingCode = b'intl'
cItem = b'citm'
cLine = b'clin'
cLongDateTime = b'ldt '
cLongFixed = b'lfxd'
cLongFixedPoint = b'lfpt'
cLongFixedRectangle = b'lfrc'
cLongInteger = b'long'
cLongPoint = b'lpnt'
cLongRectangle = b'lrct'
cMachineLoc = b'mLoc'
cMenu = b'cmnu'
cMenuItem = b'cmen'
cObject = b'cobj'
cObjectSpecifier = b'obj '
cOpenableObject = b'coob'
cOval = b'covl'

cParagraph = b'cpar'
cPICT = b'PICT'
cPixel = b'cpxl'
cPixelMap = b'cpix'
cPolygon = b'cpgn'
cProperty = b'prop'
cQDPoint = b'QDpt'
cQDRectangle = b'qdrt'
cRectangle = b'crec'
cRGBColor = b'cRGB'
cRotation = b'trot'
cRoundedRectangle = b'crrc'
cRow = b'crow'
cSelection = b'csel'
cShortInteger = b'shor'
cTable = b'ctbl'
cText = b'ctxt'
cTextFlow = b'cflo'
cTextStyles = b'tsty'
cType = b'type'

cVersion = b'vers'
cWindow = b'cwin'
cWord = b'cwor'
enumArrows = b'arro'
enumJustification = b'just'
enumKeyForm = b'kfrm'
enumPosition = b'posi'
enumProtection = b'prtn'
enumQuality = b'qual'
enumSaveOptions = b'savo'
enumStyle = b'styl'
enumTransferMode = b'tran'
kAEAbout = b'abou'
kAEAfter = b'afte'
kAEAliasSelection = b'sali'
kAEAllCaps = b'alcp'
kAEArrowAtEnd = b'aren'
kAEArrowAtStart = b'arst'
kAEArrowBothEnds = b'arbo'

kAEAsk = b'ask '
kAEBefore = b'befo'
kAEBeginning = b'bgng'
kAEBeginsWith = b'bgwt'
kAEBeginTransaction = b'begi'
kAEBold = b'bold'
kAECaseSensEquals = b'cseq'
kAECentered = b'cent'
kAEChangeView = b'view'
kAEClone = b'clon'
kAEClose = b'clos'
kAECondensed = b'cond'
kAEContains = b'cont'
kAECopy = b'copy'
kAECoreSuite = b'core'
kAECountElements = b'cnte'
kAECreateElement = b'crel'
kAECreatePublisher = b'cpub'
kAECut = b'cut '
kAEDelete = b'delo'

kAEDoObjectsExist = b'doex'
kAEDoScript = b'dosc'
kAEDrag = b'drag'
kAEDuplicateSelection = b'sdup'
kAEEditGraphic = b'edit'
kAEEmptyTrash = b'empt'
kAEEnd = b'end '
kAEEndsWith = b'ends'
kAEEndTransaction = b'endt'
kAEEquals = b'=   '
kAEExpanded = b'pexp'
kAEFast = b'fast'
kAEFinderEvents = b'FNDR'
kAEFormulaProtect = b'fpro'
kAEFullyJustified = b'full'
kAEGetClassInfo = b'qobj'
kAEGetData = b'getd'
kAEGetDataSize = b'dsiz'
kAEGetEventInfo = b'gtei'
kAEGetInfoSelection = b'sinf'

kAEGetPrivilegeSelection = b'sprv'
kAEGetSuiteInfo = b'gtsi'
kAEGreaterThan = b'>   '
kAEGreaterThanEquals = b'>=  '
kAEGrow = b'grow'
kAEHidden = b'hidn'
kAEHiQuality = b'hiqu'
kAEImageGraphic = b'imgr'
kAEIsUniform = b'isun'
kAEItalic = b'ital'
kAELeftJustified = b'left'
kAELessThan = b'<   '
kAELessThanEquals = b'<=  '
kAELowercase = b'lowc'
kAEMakeObjectsVisible = b'mvis'
kAEMiscStandards = b'misc'
kAEModifiable = b'modf'
kAEMove = b'move'
kAENo = b'no  '
kAENoArrow = b'arno'

kAENonmodifiable = b'nmod'
kAEOpen = b'odoc'
kAEOpenSelection = b'sope'
kAEOutline = b'outl'
kAEPageSetup = b'pgsu'
kAEPaste = b'past'
kAEPlain = b'plan'
kAEPrint = b'pdoc'
kAEPrintSelection = b'spri'
kAEPrintWindow = b'pwin'
kAEPutAwaySelection = b'sput'
kAEQDAddOver = b'addo'
kAEQDAddPin = b'addp'
kAEQDAdMax = b'admx'
kAEQDAdMin = b'admn'
kAEQDBic = b'bic '
kAEQDBlend = b'blnd'
kAEQDCopy = b'cpy '
kAEQDNotBic = b'nbic'
kAEQDNotCopy = b'ncpy'

kAEQDNotOr = b'ntor'
kAEQDNotXor = b'nxor'
kAEQDOr = b'or  '
kAEQDSubOver = b'subo'
kAEQDSubPin = b'subp'
kAEQDSupplementalSuite = b'qdsp'
kAEQDXor = b'xor '
kAEQuickdrawSuite = b'qdrw'
kAEQuitAll = b'quia'
kAERedo = b'redo'
kAERegular = b'regl'
kAEReopenApplication = b'rapp'
kAEReplace = b'rplc'
kAERequiredSuite = b'reqd'
kAERestart = b'rest'
kAERevealSelection = b'srev'
kAERevert = b'rvrt'
kAERightJustified = b'rght'
kAESave = b'save'
kAESelect = b'slct'
kAESetData = b'setd'

kAESetPosition = b'posn'
kAEShadow = b'shad'
kAEShowClipboard = b'shcl'
kAEShutDown = b'shut'
kAESleep = b'slep'
kAESmallCaps = b'smcp'
kAESpecialClassProperties = b'c@#!'
kAEStrikethrough = b'strk'
kAESubscript = b'sbsc'
kAESuperscript = b'spsc'
kAETableSuite = b'tbls'
kAETextSuite = b'TEXT'
kAETransactionTerminated = b'ttrm'
kAEUnderline = b'undl'
kAEUndo = b'undo'
kAEWholeWordEquals = b'wweq'
kAEYes = b'yes '
kAEZoom = b'zoom'

kAELogOut = b'logo'
kAEReallyLogOut = b'rlgo'
kAEShowRestartDialog = b'rrst'
kAEShowShutdownDialog = b'rsdn'

kAEMouseClass = b'mous'
kAEDown = b'down'
kAEUp = b'up  '
kAEMoved = b'move'
kAEStoppedMoving = b'stop'
kAEWindowClass = b'wind'
kAEUpdate = b'updt'
kAEActivate = b'actv'
kAEDeactivate = b'dact'
kAECommandClass = b'cmnd'
kAEKeyClass = b'keyc'
kAERawKey = b'rkey'
kAEVirtualKey = b'keyc'
kAENavigationKey = b'nave'
kAEAutoDown = b'auto'
kAEApplicationClass = b'appl'
kAESuspend = b'susp'
kAEResume = b'rsme'
kAEDiskEvent = b'disk'
kAENullEvent = b'null'
kAEWakeUpEvent = b'wake'
kAEScrapEvent = b'scrp'
kAEHighLevel = b'high'

keyAEAngle = b'kang'
keyAEArcAngle = b'parc'

keyAEBaseAddr = b'badd'
keyAEBestType = b'pbst'
keyAEBgndColor = b'kbcl'
keyAEBgndPattern = b'kbpt'
keyAEBounds = b'pbnd'
keyAECellList = b'kclt'
keyAEClassID = b'clID'
keyAEColor = b'colr'
keyAEColorTable = b'cltb'
keyAECurveHeight = b'kchd'
keyAECurveWidth = b'kcwd'
keyAEDashStyle = b'pdst'
keyAEData = b'data'
keyAEDefaultType = b'deft'
keyAEDefinitionRect = b'pdrt'
keyAEDescType = b'dstp'
keyAEDestination = b'dest'
keyAEDoAntiAlias = b'anta'
keyAEDoDithered = b'gdit'
keyAEDoRotate = b'kdrt'

keyAEDoScale = b'ksca'
keyAEDoTranslate = b'ktra'
keyAEEditionFileLoc = b'eloc'
keyAEElements = b'elms'
keyAEEndPoint = b'pend'
keyAEEventClass = b'evcl'
keyAEEventID = b'evti'
keyAEFile = b'kfil'
keyAEFileType = b'fltp'
keyAEFillColor = b'flcl'
keyAEFillPattern = b'flpt'
keyAEFlipHorizontal = b'kfho'
keyAEFlipVertical = b'kfvt'
keyAEFont = b'font'
keyAEFormula = b'pfor'
keyAEGraphicObjects = b'gobs'
keyAEID = b'ID  '
keyAEImageQuality = b'gqua'
keyAEInsertHere = b'insh'
keyAEKeyForms = b'keyf'

keyAEKeyword = b'kywd'
keyAELevel = b'levl'
keyAELineArrow = b'arro'
keyAEName = b'pnam'
keyAENewElementLoc = b'pnel'
keyAEObject = b'kobj'
keyAEObjectClass = b'kocl'
keyAEOffStyles = b'ofst'
keyAEOnStyles = b'onst'
keyAEParameters = b'prms'
keyAEParamFlags = b'pmfg'
keyAEPenColor = b'ppcl'
keyAEPenPattern = b'pppa'
keyAEPenWidth = b'ppwd'
keyAEPixelDepth = b'pdpt'
keyAEPixMapMinus = b'kpmm'
keyAEPMTable = b'kpmt'
keyAEPointList = b'ptlt'
keyAEPointSize = b'ptsz'
keyAEPosition = b'kpos'

keyAEPropData = b'prdt'
keyAEProperties = b'qpro'
keyAEProperty = b'kprp'
keyAEPropFlags = b'prfg'
keyAEPropID = b'prop'
keyAEProtection = b'ppro'
keyAERenderAs = b'kren'
keyAERequestedType = b'rtyp'
keyAEResult = b'----'
keyAEResultInfo = b'rsin'
keyAERotation = b'prot'
keyAERotPoint = b'krtp'
keyAERowList = b'krls'
keyAESaveOptions = b'savo'
keyAEScale = b'pscl'
keyAEScriptTag = b'psct'
keyAESearchText = b'stxt'
keyAEShowWhere = b'show'
keyAEStartAngle = b'pang'
keyAEStartPoint = b'pstp'
keyAEStyles = b'ksty'

keyAESuiteID = b'suit'
keyAEText = b'ktxt'
keyAETextColor = b'ptxc'
keyAETextFont = b'ptxf'
keyAETextPointSize = b'ptps'
keyAETextStyles = b'txst'
keyAETextLineHeight = b'ktlh'
keyAETextLineAscent = b'ktas'
keyAETheText = b'thtx'
keyAETransferMode = b'pptm'
keyAETranslation = b'ptrs'
keyAETryAsStructGraf = b'toog'
keyAEUniformStyles = b'ustl'
keyAEUpdateOn = b'pupd'
keyAEUserTerm = b'utrm'
keyAEWindow = b'wndw'
keyAEWritingCode = b'wrcd'

keyMiscellaneous = b'fmsc'
keySelection = b'fsel'
keyWindow = b'kwnd'
keyWhen = b'when'
keyWhere = b'wher'
keyModifiers = b'mods'
keyKey = b'key '
keyKeyCode = b'code'
keyKeyboard = b'keyb'
keyDriveNumber = b'drv#'
keyErrorCode = b'err#'
keyHighLevelClass = b'hcls'
keyHighLevelID = b'hid '

pArcAngle = b'parc'
pBackgroundColor = b'pbcl'
pBackgroundPattern = b'pbpt'
pBestType = b'pbst'
pBounds = b'pbnd'
pClass = b'pcls'
pClipboard = b'pcli'
pColor = b'colr'
pColorTable = b'cltb'
pContents = b'pcnt'
pCornerCurveHeight = b'pchd'
pCornerCurveWidth = b'pcwd'
pDashStyle = b'pdst'
pDefaultType = b'deft'
pDefinitionRect = b'pdrt'
pEnabled = b'enbl'
pEndPoint = b'pend'
pFillColor = b'flcl'
pFillPattern = b'flpt'
pFont = b'font'

pFormula = b'pfor'
pGraphicObjects = b'gobs'
pHasCloseBox = b'hclb'
pHasTitleBar = b'ptit'
pID = b'ID  '
pIndex = b'pidx'
pInsertionLoc = b'pins'
pIsFloating = b'isfl'
pIsFrontProcess = b'pisf'
pIsModal = b'pmod'
pIsModified = b'imod'
pIsResizable = b'prsz'
pIsStationeryPad = b'pspd'
pIsZoomable = b'iszm'
pIsZoomed = b'pzum'
pItemNumber = b'itmn'
pJustification = b'pjst'
pLineArrow = b'arro'
pMenuID = b'mnid'
pName = b'pnam'

pNewElementLoc = b'pnel'
pPenColor = b'ppcl'
pPenPattern = b'pppa'
pPenWidth = b'ppwd'
pPixelDepth = b'pdpt'
pPointList = b'ptlt'
pPointSize = b'ptsz'
pProtection = b'ppro'
pRotation = b'prot'
pScale = b'pscl'
pScript = b'scpt'
pScriptTag = b'psct'
pSelected = b'selc'
pSelection = b'sele'
pStartAngle = b'pang'
pStartPoint = b'pstp'
pTextColor = b'ptxc'
pTextFont = b'ptxf'
pTextItemDelimiters = b'txdl'
pTextPointSize = b'ptps'

pTextStyles = b'txst'
pTransferMode = b'pptm'
pTranslation = b'ptrs'
pUniformStyles = b'ustl'
pUpdateOn = b'pupd'
pUserSelection = b'pusl'
pVersion = b'vers'
pVisible = b'pvis'

typeAEText = b'tTXT'
typeArc = b'carc'
typeBest = b'best'
typeCell = b'ccel'
typeClassInfo = b'gcli'
typeColorTable = b'clrt'
typeColumn = b'ccol'
typeDashStyle = b'tdas'
typeData = b'tdta'
typeDrawingArea = b'cdrw'
typeElemInfo = b'elin'
typeEnumeration = b'enum'
typeEPS = b'EPS '
typeEventInfo = b'evin'

typeFinderWindow = b'fwin'
typeFixedPoint = b'fpnt'
typeFixedRectangle = b'frct'
typeGraphicLine = b'glin'
typeGraphicText = b'cgtx'
typeGroupedGraphic = b'cpic'
typeInsertionLoc = b'insl'
typeIntlText = b'itxt'
typeIntlWritingCode = b'intl'
typeLongDateTime = b'ldt '
typeCFAbsoluteTime = b'cfat'
typeISO8601DateTime = b'isot'
typeLongFixed = b'lfxd'
typeLongFixedPoint = b'lfpt'
typeLongFixedRectangle = b'lfrc'
typeLongPoint = b'lpnt'
typeLongRectangle = b'lrct'
typeMachineLoc = b'mLoc'
typeOval = b'covl'
typeParamInfo = b'pmin'
typePict = b'PICT'

typePixelMap = b'cpix'
typePixMapMinus = b'tpmm'
typePolygon = b'cpgn'
typePropInfo = b'pinf'
typePtr = b'ptr '
typeQDPoint = b'QDpt'
typeQDRegion = b'Qrgn'
typeRectangle = b'crec'
typeRGB16 = b'tr16'
typeRGB96 = b'tr96'
typeRGBColor = b'cRGB'
typeRotation = b'trot'
typeRoundedRectangle = b'crrc'
typeRow = b'crow'
typeScrapStyles = b'styl'
typeScript = b'scpt'
typeStyledText = b'STXT'
typeSuiteInfo = b'suin'
typeTable = b'ctbl'
typeTextStyles = b'tsty'

typeTIFF = b'TIFF'
typeJPEG = b'JPEG'
typeGIF = b'GIFf'
typeVersion = b'vers'

kAEMenuClass = b'menu'
kAEMenuSelect = b'mhit'
kAEMouseDown = b'mdwn'
kAEMouseDownInBack = b'mdbk'
kAEKeyDown = b'kdwn'
kAEResized = b'rsiz'
kAEPromise = b'prom'

keyMenuID = b'mid '
keyMenuItem = b'mitm'
keyCloseAllWindows = b'caw '
keyOriginalBounds = b'obnd'
keyNewBounds = b'nbnd'
keyLocalWhere = b'lwhr'

typeHIMenu = b'mobj'
typeHIWindow = b'wobj'

kBySmallIcon = 0
kByIconView = 1
kByNameView = 2
kByDateView = 3
kBySizeView = 4
kByKindView = 5
kByCommentView = 6
kByLabelView = 7
kByVersionView = 8

kAEInfo = 11
kAEMain = 0
kAESharing = 13

kAEZoomIn = 7
kAEZoomOut = 8

kTextServiceClass = b'tsvc'
kUpdateActiveInputArea = b'updt'
kShowHideInputWindow = b'shiw'
kPos2Offset = b'p2st'
kOffset2Pos = b'st2p'
kUnicodeNotFromInputMethod = b'unim'
kGetSelectedText = b'gtxt'
keyAETSMDocumentRefcon = b'refc'
keyAEServerInstance = b'srvi'
keyAETheData = b'kdat'
keyAEFixLength = b'fixl'
keyAEUpdateRange = b'udng'
keyAECurrentPoint = b'cpos'
keyAEBufferSize = b'buff'
keyAEMoveView = b'mvvw'
keyAENextBody = b'nxbd'
keyAETSMScriptTag = b'sclg'
keyAETSMTextFont = b'ktxf'
keyAETSMTextFMFont = b'ktxm'
keyAETSMTextPointSize = b'ktps'
keyAETSMEventRecord = b'tevt'
keyAETSMEventRef = b'tevr'
keyAETextServiceEncoding = b'tsen'
keyAETextServiceMacEncoding = b'tmen'
keyAETSMGlyphInfoArray = b'tgia'
typeTextRange = b'txrn'
typeComponentInstance = b'cmpi'
typeOffsetArray = b'ofay'
typeTextRangeArray = b'tray'
typeLowLevelEventRecord = b'evtr'
typeGlyphInfoArray = b'glia'
typeEventRef = b'evrf'
typeText = typeChar

kTSMOutsideOfBody = 1
kTSMInsideOfBody = 2
kTSMInsideOfActiveInputArea = 3

kNextBody = 1
kPreviousBody = 2

kTSMHiliteCaretPosition = 1
kTSMHiliteRawText = 2
kTSMHiliteSelectedRawText = 3
kTSMHiliteConvertedText = 4
kTSMHiliteSelectedConvertedText = 5
kTSMHiliteBlockFillText = 6
kTSMHiliteOutlineText = 7
kTSMHiliteSelectedText = 8
kTSMHiliteNoHilite = 9

kCaretPosition = kTSMHiliteCaretPosition
kRawText = kTSMHiliteRawText
kSelectedRawText = kTSMHiliteSelectedRawText
kConvertedText = kTSMHiliteConvertedText
kSelectedConvertedText = kTSMHiliteSelectedConvertedText
kBlockFillText = kTSMHiliteBlockFillText
kOutlineText = kTSMHiliteOutlineText
kSelectedText = kTSMHiliteSelectedText

keyAEHiliteRange = b'hrng'
keyAEPinRange = b'pnrg'
keyAEClauseOffsets = b'clau'
keyAEOffset = b'ofst'
keyAEPoint = b'gpos'
keyAELeftSide = b'klef'
keyAERegionClass = b'rgnc'
keyAEDragging = b'bool'

keyAELeadingEdge = keyAELeftSide

typeMeters = b'metr'
typeInches = b'inch'
typeFeet = b'feet'
typeYards = b'yard'
typeMiles = b'mile'
typeKilometers = b'kmtr'
typeCentimeters = b'cmtr'
typeSquareMeters = b'sqrm'
typeSquareFeet = b'sqft'
typeSquareYards = b'sqyd'
typeSquareMiles = b'sqmi'
typeSquareKilometers = b'sqkm'
typeLiters = b'litr'
typeQuarts = b'qrts'
typeGallons = b'galn'
typeCubicMeters = b'cmet'
typeCubicFeet = b'cfet'
typeCubicInches = b'cuin'
typeCubicCentimeter = b'ccmt'
typeCubicYards = b'cyrd'
typeKilograms = b'kgrm'
typeGrams = b'gram'
typeOunces = b'ozs '
typePounds = b'lbs '
typeDegreesC = b'degc'
typeDegreesF = b'degf'
typeDegreesK = b'degk'

kFAServerApp = b'ssrv'
kDoFolderActionEvent = b'fola'
kFolderActionCode = b'actn'
kFolderOpenedEvent = b'fopn'
kFolderClosedEvent = b'fclo'
kFolderWindowMovedEvent = b'fsiz'
kFolderItemsAddedEvent = b'fget'
kFolderItemsRemovedEvent = b'flos'
kItemList = b'flst'
kNewSizeParameter = b'fnsz'
kFASuiteCode = b'faco'
kFAAttachCommand = b'atfa'
kFARemoveCommand = b'rmfa'
kFAEditCommand = b'edfa'
kFAFileParam = b'faal'
kFAIndexParam = b'indx'

kAEInternetSuite = b'gurl'
kAEISWebStarSuite = b'WWW\xBD'

kAEISGetURL = b'gurl'
KAEISHandleCGI = b'sdoc'

cURL = b'url '
cInternetAddress = b'IPAD'
cHTML = b'html'
cFTPItem = b'ftp '

kAEISHTTPSearchArgs = b'kfor'
kAEISPostArgs = b'post'
kAEISMethod = b'meth'
kAEISClientAddress = b'addr'
kAEISUserName = b'user'
kAEISPassword = b'pass'
kAEISFromUser = b'frmu'
kAEISServerName = b'svnm'
kAEISServerPort = b'svpt'
kAEISScriptName = b'scnm'
kAEISContentType = b'ctyp'
kAEISReferrer = b'refr'
kAEISUserAgent = b'Agnt'
kAEISAction = b'Kact'
kAEISActionPath = b'Kapt'
kAEISClientIP = b'Kcip'
kAEISFullRequest = b'Kfrq'

pScheme = b'pusc'
pHost = b'HOST'
pPath = b'FTPc'
pUserName = b'RAun'
pUserPassword = b'RApw'
pDNSForm = b'pDNS'
pURL = b'pURL'
pTextEncoding = b'ptxe'
pFTPKind = b'kind'

eScheme = b'esch'
eurlHTTP = b'http'
eurlHTTPS = b'htps'
eurlFTP = b'ftp '
eurlMail = b'mail'
eurlFile = b'file'
eurlGopher = b'gphr'
eurlTelnet = b'tlnt'
eurlNews = b'news'
eurlSNews = b'snws'
eurlNNTP = b'nntp'
eurlMessage = b'mess'
eurlMailbox = b'mbox'
eurlMulti = b'mult'
eurlLaunch = b'laun'
eurlAFP = b'afp '
eurlAT = b'at  '
eurlEPPC = b'eppc'
eurlRTSP = b'rtsp'
eurlIMAP = b'imap'
eurlNFS = b'unfs'
eurlPOP = b'upop'
eurlLDAP = b'uldp'
eurlUnknown = b'url?'

kConnSuite = b'macc'
cDevSpec = b'cdev'
cAddressSpec = b'cadr'
cADBAddress = b'cadb'
cAppleTalkAddress = b'cat '
cBusAddress = b'cbus'
cEthernetAddress = b'cen '
cFireWireAddress = b'cfw '
cIPAddress = b'cip '
cLocalTalkAddress = b'clt '
cSCSIAddress = b'cscs'
cTokenRingAddress = b'ctok'
cUSBAddress = b'cusb'
pDeviceType = b'pdvt'
pDeviceAddress = b'pdva'
pConduit = b'pcon'
pProtocol = b'pprt'
pATMachine = b'patm'
pATZone = b'patz'
pATType = b'patt'
pDottedDecimal = b'pipd'
pDNS = b'pdns'
pPort = b'ppor'
pNetwork = b'pnet'
pNode = b'pnod'
pSocket = b'psoc'
pSCSIBus = b'pscb'
pSCSILUN = b'pslu'
eDeviceType = b'edvt'
eAddressSpec = b'eads'
eConduit = b'econ'
eProtocol = b'epro'
eADB = b'eadb'
eAnalogAudio = b'epau'
eAppleTalk = b'epat'
eAudioLineIn = b'ecai'
eAudioLineOut = b'ecal'
eAudioOut = b'ecao'
eBus = b'ebus'
eCDROM = b'ecd '
eCommSlot = b'eccm'
eDigitalAudio = b'epda'
eDisplay = b'edds'
eDVD = b'edvd'
eEthernet = b'ecen'
eFireWire = b'ecfw'
eFloppy = b'efd '
eHD = b'ehd '
eInfrared = b'ecir'
eIP = b'epip'
eIrDA = b'epir'
eIRTalk = b'epit'
eKeyboard = b'ekbd'
eLCD = b'edlc'
eLocalTalk = b'eclt'
eMacIP = b'epmi'
eMacVideo = b'epmv'
eMicrophone = b'ecmi'
eModemPort = b'ecmp'
eModemPrinterPort = b'empp'
eModem = b'edmm'
eMonitorOut = b'ecmn'
eMouse = b'emou'
eNuBusCard = b'ednb'
eNuBus = b'enub'
ePCcard = b'ecpc'
ePCIbus = b'ecpi'
ePCIcard = b'edpi'
ePDSslot = b'ecpd'
ePDScard = b'epds'
ePointingDevice = b'edpd'
ePostScript = b'epps'
ePPP = b'eppp'
ePrinterPort = b'ecpp'
ePrinter = b'edpr'
eSvideo = b'epsv'
eSCSI = b'ecsc'
eSerial = b'epsr'
eSpeakers = b'edsp'
eStorageDevice = b'edst'
eSVGA = b'epsg'
eTokenRing = b'etok'
eTrackball = b'etrk'
eTrackpad = b'edtp'
eUSB = b'ecus'
eVideoIn = b'ecvi'
eVideoMonitor = b'edvm'
eVideoOut = b'ecvo'

cKeystroke = b'kprs'
pKeystrokeKey = b'kMsg'
pModifiers = b'kMod'
pKeyKind = b'kknd'
eModifiers = b'eMds'
eOptionDown = b'Kopt'
eCommandDown = b'Kcmd'
eControlDown = b'Kctl'
eShiftDown = b'Ksft'
eCapsLockDown = b'Kclk'
eKeyKind = b'ekst'
eEscapeKey = b'ks5\x00'
eDeleteKey = b'ks3\x00'
eTabKey = b'ks0\x00'
eReturnKey = b'ks\x24\x00'
eClearKey = b'ksG\x00'
eEnterKey = b'ksL\x00'
eUpArrowKey = b'ks\x7E\x00'
eDownArrowKey = b'ks\x7D\x00'
eLeftArrowKey = b'ks\x7B\x00'
eRightArrowKey = b'ks\x7C\x00'
eHelpKey = b'ksr\x00'
eHomeKey = b'kss\x00'
ePageUpKey = b'kst\x00'
ePageDownKey = b'ksy\x00'
eForwardDelKey = b'ksu\x00'
eEndKey = b'ksw\x00'
eF1Key = b'ksz\x00'
eF2Key = b'ksx\x00'
eF3Key = b'ksc\x00'
eF4Key = b'ksv\x00'
eF5Key = b'ks\x60\x00'
eF6Key = b'ksa\x00'
eF7Key = b'ksb\x00'
eF8Key = b'ksd\x00'
eF9Key = b'kse\x00'
eF10Key = b'ksm\x00'
eF11Key = b'ksg\x00'
eF12Key = b'kso\x00'
eF13Key = b'ksi\x00'
eF14Key = b'ksk\x00'
eF15Key = b'ksq\x00'

keyAELaunchedAsLogInItem = b'lgit'
keyAELaunchedAsServiceItem = b'svit'



# AEUserTermTypes.h

kAEUserTerminology = b'aeut'
kAETerminologyExtension = b'aete'
kAEScriptingSizeResource = b'scsz'
kAEOSAXSizeResource = b'osiz'

kAEUTHasReturningParam = 31
kAEUTOptional = 15
kAEUTlistOfItems = 14
kAEUTEnumerated = 13
kAEUTReadWrite = 12
kAEUTChangesState = 12
kAEUTTightBindingFunction = 12
kAEUTEnumsAreTypes = 11
kAEUTEnumListIsExclusive = 10
kAEUTReplyIsReference = 9
kAEUTDirectParamIsReference = 9
kAEUTParamIsReference = 9
kAEUTPropertyIsReference = 9
kAEUTNotDirectParamIsTarget = 8
kAEUTParamIsTarget = 8
kAEUTApostrophe = 3
kAEUTFeminine = 2
kAEUTMasculine = 1
kAEUTPlural = 0

kLaunchToGetTerminology = (1 << 15)
kDontFindAppBySignature = (1 << 14)
kAlwaysSendSubject = (1 << 13)

kReadExtensionTermsMask = (1 << 15)

kOSIZDontOpenResourceFile = 15
kOSIZdontAcceptRemoteEvents = 14
kOSIZOpenWithReadPermission = 13
kOSIZCodeInSharedLibraries = 11



# AppleEvents.h

keyDirectObject = b'----'
keyErrorNumber = b'errn'
keyErrorString = b'errs'
keyProcessSerialNumber = b'psn '
keyPreDispatch = b'phac'
keySelectProc = b'selh'
keyAERecorderCount = b'recr'
keyAEVersion = b'vers'

kCoreEventClass = b'aevt'

kAEOpenApplication = b'oapp'
kAEOpenDocuments = b'odoc'
kAEPrintDocuments = b'pdoc'
kAEOpenContents = b'ocon'
kAEQuitApplication = b'quit'
kAEAnswer = b'ansr'
kAEApplicationDied = b'obit'
kAEShowPreferences = b'pref'

kAEStartRecording = b'reca'
kAEStopRecording = b'recc'
kAENotifyStartRecording = b'rec1'
kAENotifyStopRecording = b'rec0'
kAENotifyRecording = b'recr'

kAEUnknownSource = 0
kAEDirectCall = 1
kAESameProcess = 2
kAELocalProcess = 3
kAERemoteProcess = 4



# AEInteraction.h

kAEInteractWithSelf = 0
kAEInteractWithLocal = 1
kAEInteractWithAll = 2

kAEDoNotIgnoreHandler = 0x00000000
kAEIgnoreAppPhacHandler = 0x00000001
kAEIgnoreAppEventHandler = 0x00000002
kAEIgnoreSysPhacHandler = 0x00000004
kAEIgnoreSysEventHandler = 0x00000008
kAEIngoreBuiltInEventHandler = 0x00000010
kAEDontDisposeOnResume = 0x80000000

kAENoDispatch = 0
kAEUseStandardDispatch = 0xFFFFFFFF



# AppleScript.h

typeAppleScript = b'ascr'
kAppleScriptSubtype = typeAppleScript
typeASStorage = typeAppleScript

kASSelectInit = 0x1001
kASSelectSetSourceStyles = 0x1002
kASSelectGetSourceStyles = 0x1003
kASSelectGetSourceStyleNames = 0x1004
kASSelectCopySourceAttributes = 0x1005
kASSelectSetSourceAttributes = 0x1006

kASHasOpenHandler = b'hsod'

kASDefaultMinStackSize = 4
kASDefaultPreferredStackSize = 16
kASDefaultMaxStackSize = 16
kASDefaultMinHeapSize = 4
kASDefaultPreferredHeapSize = 16
kASDefaultMaxHeapSize = 32

kASSourceStyleUncompiledText = 0
kASSourceStyleNormalText = 1
kASSourceStyleLanguageKeyword = 2
kASSourceStyleApplicationKeyword = 3
kASSourceStyleComment = 4
kASSourceStyleLiteral = 5
kASSourceStyleUserSymbol = 6
kASSourceStyleObjectSpecifier = 7
kASNumberOfSourceStyles = 8



# ASDebugging.h

kOSAModeDontDefine = 0x0001

kASSelectSetPropertyObsolete = 0x1101
kASSelectGetPropertyObsolete = 0x1102
kASSelectSetHandlerObsolete = 0x1103
kASSelectGetHandlerObsolete = 0x1104
kASSelectGetAppTerminologyObsolete = 0x1105
kASSelectSetProperty = 0x1106
kASSelectGetProperty = 0x1107
kASSelectSetHandler = 0x1108
kASSelectGetHandler = 0x1109
kASSelectGetAppTerminology = 0x110A
kASSelectGetSysTerminology = 0x110B
kASSelectGetPropertyNames = 0x110C
kASSelectGetHandlerNames = 0x110D



# ASRegistry.h

keyAETarget = b'targ'
keySubjectAttr = b'subj'
keyASReturning = b'Krtn'
kASAppleScriptSuite = b'ascr'
kASScriptEditorSuite = b'ToyS'
kASTypeNamesSuite = b'tpnm'
typeAETE = b'aete'
typeAEUT = b'aeut'
kGetAETE = b'gdte'
kGetAEUT = b'gdut'
kUpdateAEUT = b'udut'
kUpdateAETE = b'udte'
kCleanUpAEUT = b'cdut'
kASComment = b'cmnt'
kASLaunchEvent = b'noop'
keyScszResource = b'scsz'
typeScszResource = b'scsz'
kASSubroutineEvent = b'psbr'
keyASSubroutineName = b'snam'
kASPrepositionalSubroutine = b'psbr'
keyASPositionalArgs = b'parg'

keyAppHandledCoercion = b'idas'

kASStartLogEvent = b'log1'
kASStopLogEvent = b'log0'
kASCommentEvent = b'cmnt'

kASAdd = b'+   '
kASSubtract = b'-   '
kASMultiply = b'*   '
kASDivide = b'/   '
kASQuotient = b'div '
kASRemainder = b'mod '
kASPower = b'^   '
kASEqual = kAEEquals
kASNotEqual = 0xAD202020
kASGreaterThan = kAEGreaterThan
kASGreaterThanOrEqual = kAEGreaterThanEquals
kASLessThan = kAELessThan
kASLessThanOrEqual = kAELessThanEquals
kASComesBefore = b'cbfr'
kASComesAfter = b'cafr'
kASConcatenate = b'ccat'
kASStartsWith = kAEBeginsWith
kASEndsWith = kAEEndsWith
kASContains = kAEContains

kASAnd = kAEAND
kASOr = kAEOR
kASNot = kAENOT
kASNegate = b'neg '
keyASArg = b'arg '

kASErrorEventCode = b'err '
kOSAErrorArgs = b'erra'
keyAEErrorObject = b'erob'
pLength = b'leng'
pReverse = b'rvse'
pRest = b'rest'
pInherits = b'c@#^'
pProperties = b'pALL'
keyASUserRecordFields = b'usrf'
typeUserRecordFields = typeAEList

keyASPrepositionAt = b'at  '
keyASPrepositionIn = b'in  '
keyASPrepositionFrom = b'from'
keyASPrepositionFor = b'for '
keyASPrepositionTo = b'to  '
keyASPrepositionThru = b'thru'
keyASPrepositionThrough = b'thgh'
keyASPrepositionBy = b'by  '
keyASPrepositionOn = b'on  '
keyASPrepositionInto = b'into'
keyASPrepositionOnto = b'onto'
keyASPrepositionBetween = b'btwn'
keyASPrepositionAgainst = b'agst'
keyASPrepositionOutOf = b'outo'
keyASPrepositionInsteadOf = b'isto'
keyASPrepositionAsideFrom = b'asdf'
keyASPrepositionAround = b'arnd'
keyASPrepositionBeside = b'bsid'
keyASPrepositionBeneath = b'bnth'
keyASPrepositionUnder = b'undr'

keyASPrepositionOver = b'over'
keyASPrepositionAbove = b'abve'
keyASPrepositionBelow = b'belw'
keyASPrepositionApartFrom = b'aprt'
keyASPrepositionGiven = b'givn'
keyASPrepositionWith = b'with'
keyASPrepositionWithout = b'wout'
keyASPrepositionAbout = b'abou'
keyASPrepositionSince = b'snce'
keyASPrepositionUntil = b'till'

kDialectBundleResType = b'Dbdl'
cConstant = typeEnumerated
cClassIdentifier = pClass
cObjectBeingExamined = typeObjectBeingExamined
cList = typeAEList
cSmallReal = typeIEEE32BitFloatingPoint
cReal = typeIEEE64BitFloatingPoint
cRecord = typeAERecord
cReference = cObjectSpecifier
cUndefined = b'undf'
cMissingValue = b'msng'
cSymbol = b'symb'
cLinkedList = b'llst'
cVector = b'vect'
cEventIdentifier = b'evnt'
cKeyIdentifier = b'kyid'
cUserIdentifier = b'uid '
cPreposition = b'prep'
cKeyForm = enumKeyForm
cScript = b'scpt'
cHandler = b'hand'
cProcedure = b'proc'

cHandleBreakpoint = b'brak'

cClosure = b'clsr'
cRawData = b'rdat'
cStringClass = typeChar
cNumber = b'nmbr'
cListElement = b'celm'
cListOrRecord = b'lr  '
cListOrString = b'ls  '
cListRecordOrString = b'lrs '
cNumberOrString = b'ns  '
cNumberOrDateTime = b'nd  '
cNumberDateTimeOrString = b'nds '
cAliasOrString = b'sf  '
cSeconds = b'scnd'
typeSound = b'snd '
enumBooleanValues = b'boov'
kAETrue = typeTrue
kAEFalse = typeFalse
enumMiscValues = b'misc'
kASCurrentApplication = b'cura'
formUserPropertyID = b'usrp'

cString = cStringClass

pASIt = b'it  '
pASMe = b'me  '
pASResult = b'rslt'
pASSpace = b'spac'
pASReturn = b'ret '
pASTab = b'tab '
pASPi = b'pi  '
pASParent = b'pare'
kASInitializeEventCode = b'init'
pASPrintLength = b'prln'
pASPrintDepth = b'prdp'
pASTopLevelScript = b'ascr'

kAECase = b'case'
kAEDiacritic = b'diac'
kAEWhiteSpace = b'whit'
kAEHyphens = b'hyph'
kAEExpansion = b'expa'
kAEPunctuation = b'punc'
kAEZenkakuHankaku = b'zkhk'
kAESmallKana = b'skna'
kAEKataHiragana = b'hika'
kASConsiderReplies = b'rmte'
kASNumericStrings = b'nume'
enumConsiderations = b'cons'

kAECaseConsiderMask = 0x00000001
kAEDiacriticConsiderMask = 0x00000002
kAEWhiteSpaceConsiderMask = 0x00000004
kAEHyphensConsiderMask = 0x00000008
kAEExpansionConsiderMask = 0x00000010
kAEPunctuationConsiderMask = 0x00000020
kASConsiderRepliesConsiderMask = 0x00000040
kASNumericStringsConsiderMask = 0x00000080
kAECaseIgnoreMask = 0x00010000
kAEDiacriticIgnoreMask = 0x00020000
kAEWhiteSpaceIgnoreMask = 0x00040000
kAEHyphensIgnoreMask = 0x00080000
kAEExpansionIgnoreMask = 0x00100000
kAEPunctuationIgnoreMask = 0x00200000
kASConsiderRepliesIgnoreMask = 0x00400000
kASNumericStringsIgnoreMask = 0x00800000
enumConsidsAndIgnores = b'csig'

cCoercion = b'coec'
cCoerceUpperCase = b'txup'
cCoerceLowerCase = b'txlo'
cCoerceRemoveDiacriticals = b'txdc'
cCoerceRemovePunctuation = b'txpc'
cCoerceRemoveHyphens = b'txhy'
cCoerceOneByteToTwoByte = b'txex'
cCoerceRemoveWhiteSpace = b'txws'
cCoerceSmallKana = b'txsk'
cCoerceZenkakuhankaku = b'txze'
cCoerceKataHiragana = b'txkh'
cZone = b'zone'
cMachine = b'mach'
cAddress = b'addr'
cRunningAddress = b'radd'
cStorage = b'stor'

pASWeekday = b'wkdy'
pASMonth = b'mnth'
pASDay = b'day '
pASYear = b'year'
pASTime = b'time'
pASDateString = b'dstr'
pASTimeString = b'tstr'
cMonth = pASMonth
cJanuary = b'jan '
cFebruary = b'feb '
cMarch = b'mar '
cApril = b'apr '
cMay = b'may '
cJune = b'jun '
cJuly = b'jul '
cAugust = b'aug '
cSeptember = b'sep '
cOctober = b'oct '
cNovember = b'nov '
cDecember = b'dec '

cWeekday = pASWeekday
cSunday = b'sun '
cMonday = b'mon '
cTuesday = b'tue '
cWednesday = b'wed '
cThursday = b'thu '
cFriday = b'fri '
cSaturday = b'sat '
pASQuote = b'quot'
pASSeconds = b'secs'
pASMinutes = b'min '
pASHours = b'hour'
pASDays = b'days'
pASWeeks = b'week'
cWritingCodeInfo = b'citl'
pScriptCode = b'pscd'
pLangCode = b'plcd'
kASMagicTellEvent = b'tell'
kASMagicEndTellEvent = b'tend'



# DigitalHubRegistry.h

kDigiHubEventClass = b'dhub'

kDigiHubMusicCD = b'aucd'
kDigiHubPictureCD = b'picd'
kDigiHubVideoDVD = b'vdvd'
kDigiHubBlankCD = b'bcd '
kDigiHubBlankDVD = b'bdvd'



# OSA.h

kOSAComponentType = b'osa '

kOSAGenericScriptingComponentSubtype = b'scpt'

kOSAFileType = b'osas'

kOSASuite = b'ascr'

kOSARecordedText = b'recd'

kOSAScriptIsModified = b'modi'

kOSAScriptIsTypeCompiledScript = b'cscr'

kOSAScriptIsTypeScriptValue = b'valu'

kOSAScriptIsTypeScriptContext = b'cntx'

kOSAScriptBestType = b'best'

kOSACanGetSource = b'gsrc'

typeOSADialectInfo = b'difo'
keyOSADialectName = b'dnam'
keyOSADialectCode = b'dcod'
keyOSADialectLangCode = b'dlcd'
keyOSADialectScriptCode = b'dscd'

kOSANullScript = 0

kOSANullMode = 0
kOSAModeNull = 0

kOSASupportsCompiling = 0x0002
kOSASupportsGetSource = 0x0004
kOSASupportsAECoercion = 0x0008
kOSASupportsAESending = 0x0010
kOSASupportsRecording = 0x0020
kOSASupportsConvenience = 0x0040
kOSASupportsDialects = 0x0080
kOSASupportsEventHandling = 0x0100

kOSASelectLoad = 0x0001
kOSASelectStore = 0x0002
kOSASelectExecute = 0x0003
kOSASelectDisplay = 0x0004
kOSASelectScriptError = 0x0005
kOSASelectDispose = 0x0006
kOSASelectSetScriptInfo = 0x0007
kOSASelectGetScriptInfo = 0x0008
kOSASelectSetActiveProc = 0x0009
kOSASelectGetActiveProc = 0x000A
kOSASelectCopyDisplayString = 0x000B

kOSASelectScriptingComponentName = 0x0102
kOSASelectCompile = 0x0103
kOSASelectCopyID = 0x0104

kOSASelectCopyScript = 0x0105

kOSASelectGetSource = 0x0201
kOSASelectCopySourceString = 0x0202

kOSASelectCoerceFromDesc = 0x0301
kOSASelectCoerceToDesc = 0x0302

kOSASelectSetSendProc = 0x0401
kOSASelectGetSendProc = 0x0402
kOSASelectSetCreateProc = 0x0403
kOSASelectGetCreateProc = 0x0404
kOSASelectSetDefaultTarget = 0x0405

kOSASelectStartRecording = 0x0501
kOSASelectStopRecording = 0x0502

kOSASelectLoadExecute = 0x0601
kOSASelectCompileExecute = 0x0602
kOSASelectDoScript = 0x0603

kOSASelectSetCurrentDialect = 0x0701
kOSASelectGetCurrentDialect = 0x0702
kOSASelectAvailableDialects = 0x0703
kOSASelectGetDialectInfo = 0x0704
kOSASelectAvailableDialectCodeList = 0x0705

kOSASelectSetResumeDispatchProc = 0x0801
kOSASelectGetResumeDispatchProc = 0x0802
kOSASelectExecuteEvent = 0x0803
kOSASelectDoEvent = 0x0804
kOSASelectMakeContext = 0x0805

kOSASelectComponentSpecificStart = 0x1001

kOSAModePreventGetSource = 0x00000001

kOSAModeNeverInteract = kAENeverInteract
kOSAModeCanInteract = kAECanInteract
kOSAModeAlwaysInteract = kAEAlwaysInteract
kOSAModeDontReconnect = kAEDontReconnect

kOSAModeCantSwitchLayer = 0x00000040

kOSAModeDoRecord = 0x00001000

kOSAModeCompileIntoContext = 0x00000002

kOSAModeAugmentContext = 0x00000004

kOSAModeDisplayForHumans = 0x00000008

kOSAModeDontStoreParent = 0x00010000

kOSAModeDispatchToDirectObject = 0x00020000

kOSAModeDontGetDataForArguments = 0x00040000

kOSAModeFullyQualifyDescriptors = 0x00080000

kOSAScriptResourceType = kOSAGenericScriptingComponentSubtype

typeOSAGenericStorage = kOSAScriptResourceType

kOSAErrorNumber = keyErrorNumber

kOSAErrorMessage = keyErrorString

kOSAErrorBriefMessage = b'errb'

kOSAErrorApp = b'erap'

kOSAErrorPartialResult = b'ptlr'

kOSAErrorOffendingObject = b'erob'

kOSAErrorExpectedType = b'errt'

kOSAErrorRange = b'erng'

typeOSAErrorRange = b'erng'

keyOSASourceStart = b'srcs'

keyOSASourceEnd = b'srce'

kOSAUseStandardDispatch = kAEUseStandardDispatch

kOSANoDispatch = kAENoDispatch

kOSADontUsePhac = 0x0001



# OSAComp.h



# OSAGeneric.h

kGenericComponentVersion = 0x0100

kGSSSelectGetDefaultScriptingComponent = 0x1001
kGSSSelectSetDefaultScriptingComponent = 0x1002
kGSSSelectGetScriptingComponent = 0x1003
kGSSSelectGetScriptingComponentFromStored = 0x1004
kGSSSelectGenericToRealID = 0x1005
kGSSSelectRealToGenericID = 0x1006
kGSSSelectOutOfRange = 0x1007



# Miscellaneous

