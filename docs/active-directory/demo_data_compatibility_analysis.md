# Demo Data Compatibility Analysis

## Summary
Analyzing `jukebox.internal.tdf` demo data against `Convert-DataToADObjects` function and CSVDE export requirements.

## Demo Data Properties Found

Looking at sample user entries, the demo data uses these properties:
- Name, SamAccountName, UserPrincipalName, Email
- Title, Department, Company, Manager
- Phone, MobilePhone, Office
- Street, City, PostalCode, Country
- OU, Groups, Description
- LastLogonDate
- Disabled, Locked, MustChangePassword
- AuditLog

## Convert-DataToADObjects Mapping

### ✅ CORRECTLY MAPPED Properties

The function correctly creates these AD properties:

| Demo Data Property | AD Property Created | Status |
|-------------------|-------------------|--------|
| N/A | `whenCreated` | ✅ Generated: `(Get-Date).AddDays(-90)` |
| N/A | `whenChanged` | ✅ Generated: `(Get-Date).AddDays(-5)` |
| N/A | `BadLogonCount` | ✅ Generated based on Locked status |
| Groups | `MemberOf` AND `Groups` | ✅ Both created (supports fallback) |
| N/A | `member` | ✅ For groups (Members property) |
| Email | `mail` AND `EmailAddress` | ✅ Both created |
| N/A | `pwdLastSet` | ✅ Generated: `134091109521968821` or `0` |

### ✅ All Required CSVDE Properties Are Generated

The conversion function creates ALL the properties needed for CSVDE export:

**Core Properties:**
- ✅ ObjectClass
- ✅ Name
- ✅ Domain (extracted from email or default)
- ✅ SamAccountName (from demo or generated)
- ✅ UserPrincipalName (from demo or generated)
- ✅ DisplayName (= Name)
- ✅ GivenName (first word of Name)
- ✅ Surname (last word of Name)
- ✅ DistinguishedName (generated from OU path)
- ✅ ObjectGUID (fake GUID generated)
- ✅ SID (fake SID generated)

**Timestamps:**
- ✅ whenCreated (hardcoded: 90 days ago)
- ✅ whenChanged (hardcoded: 5 days ago)
- ✅ PasswordLastSet (hardcoded: 30 days ago)
- ✅ pwdLastSet (FileTime format)
- ✅ LastLogonDate (from demo or random)

**Status Properties:**
- ✅ Enabled (inverted from Disabled)
- ✅ Disabled (from demo)
- ✅ LockedOut AND Locked (both set from demo)
- ✅ PasswordExpired (from MustChangePassword)
- ✅ BadLogonCount (3-10 if locked, else 0)

**User Details:**
- ✅ Title, Department, Company, Manager
- ✅ EmailAddress AND mail (both set)
- ✅ OfficePhone, MobilePhone, Office
- ✅ StreetAddress, City, PostalCode, Country
- ✅ Description
- ✅ MemberOf AND Groups (both set)

**AD Metadata:**
- ✅ OU (preserved from demo)
- ✅ AuditLog (preserved from demo)

## Property Preservation Feature

The function has **excellent** extra property preservation:

```powershell
## Preserve all extra user properties (LAPS, TPM, BitLocker, etc.)
if ($user -is [hashtable]) {
  foreach ($prop in $user.Keys) {
    if ($prop -in $standardProps) { continue }
    if ($null -ne $user[$prop] -and $user[$prop] -ne '') {
      $adUser | Add-Member -NotePropertyName $prop -NotePropertyValue $user[$prop] -Force
    }
  }
}
```

This means ANY custom property in demo data will be preserved in the AD object!

## Potential Issues Analysis

### ⚠️ Non-Standard Properties in Demo Data

**These properties exist in demo data but are NOT standard AD schema:**

1. **Department** ⚠️
   - Present in demo: ✅
   - Mapped by converter: ✅
   - In CSVDE export: ✅
   - **Issue**: NOT in real AD schema (per csvde.exe sample)
   - **Impact**: Will export but may be empty on re-import to real AD

2. **Company** ⚠️
   - Present in demo: ✅
   - Mapped by converter: ✅
   - In CSVDE export: ✅
   - **Issue**: NOT in real AD schema (per csvde.exe sample)
   - **Impact**: Will export but may be empty on re-import to real AD

3. **MobilePhone** ⚠️
   - Present in demo: ✅ (as `MobilePhone`)
   - Mapped by converter: ✅ (as `MobilePhone`)
   - In real AD: Should be `mobile` (lowercase, standard attribute)
   - **Issue**: Property name doesn't match AD schema
   - **Impact**: May not export correctly in CSVDE

4. **OfficePhone** ⚠️
   - Present in demo: ✅ (as `Phone`)
   - Mapped by converter: ✅ (as `OfficePhone`)
   - In real AD: Should be `telephoneNumber` (standard attribute)
   - **Issue**: Property name doesn't match AD schema
   - **Impact**: May not export correctly in CSVDE

5. **Office** ⚠️
   - Present in demo: ✅
   - Mapped by converter: ✅
   - In real AD: Should be `physicalDeliveryOfficeName` (standard attribute)
   - **Issue**: Property name doesn't match AD schema
   - **Impact**: May not export correctly in CSVDE

6. **StreetAddress** ⚠️
   - Present in demo: ✅ (as `Street`)
   - Mapped by converter: ✅ (as `StreetAddress`)
   - In real AD: Should be `streetAddress` (lowercase 's')
   - **Issue**: Case sensitivity might matter
   - **Impact**: Minor - usually case-insensitive

7. **Manager** ⚠️
   - Present in demo: ✅ (as name string)
   - Mapped by converter: ✅ (as name string)
   - In real AD: Should be DN (Distinguished Name)
   - **Issue**: Format mismatch
   - **Impact**: Will export incorrectly (needs DN format)

### ✅ Properties That Work Perfectly

These demo properties map correctly to AD:
- Name → name ✅
- SamAccountName → sAMAccountName ✅
- UserPrincipalName → userPrincipalName ✅
- Email → mail ✅
- Title → title ✅
- Description → description ✅
- Country → country (or countryCode) ✅
- City → city (or l for locality) ✅
- PostalCode → postalCode ✅
- Groups → memberOf ✅

## Missing Standard AD Properties

Properties that SHOULD be in demo data but aren't:

### High Priority Missing
1. **primaryGroupID** - Not in demo, converter doesn't set
   - Recommendation: Add to converter with default 513
2. **groupType** - Not in demo for groups
   - Recommendation: Add to converter with default -2147483646
3. **objectCategory** - Not generated
   - Recommendation: Add to converter
4. **cn** - Not generated (name is used instead)
   - Recommendation: Add to converter (`cn = $obj.Name`)
5. **instanceType** - Not generated
   - Recommendation: Add to converter with value 4

### Medium Priority Missing
6. **adminCount** - Could be useful for some users
7. **logonCount** - Not tracked in demo
8. **badPasswordTime** - Not tracked

## Recommendations

### 1. Update Convert-DataToADObjects Function

Add these property mappings for better AD compatibility:

```powershell
## For USERS - add to $adUser object:
cn                     = $user.Name
instanceType          = 4
primaryGroupID        = 513  # Domain Users
telephoneNumber       = $user.Phone
mobile                = $user.MobilePhone
physicalDeliveryOfficeName = $user.Office
objectCategory        = "CN=Person,CN=Schema,CN=Configuration,$BaseDN"

## For GROUPS - add to $adGroup object:
cn                     = $group.Name
instanceType          = 4
groupType             = -2147483646  # Global Security
objectCategory        = "CN=Group,CN=Schema,CN=Configuration,$BaseDN"

## For COMPUTERS/DCs - add:
cn                     = $computer.Name
instanceType          = 4
objectCategory        = "CN=Computer,CN=Schema,CN=Configuration,$BaseDN"
```

### 2. Fix Manager Property

Convert manager name to DN format:
```powershell
Manager = if ($user.Manager) {
  "CN=$($user.Manager),$BaseDN"
} else { "" }
```

### 3. Update CSVDE Export

The CSVDE export should use these mappings:
- `telephoneNumber` (not OfficePhone)
- `mobile` (not MobilePhone)  
- `physicalDeliveryOfficeName` (not Office)
- `cn` (common name - same as name)
- `primaryGroupID`, `groupType`, `objectCategory`, `instanceType`

### 4. Document Non-Standard Properties

Add comments noting that these are demo-only:
- Department
- Company

## Conclusion

### Current Status
- ✅ Core AD properties are correctly mapped
- ✅ Critical CSVDE properties (whenCreated, whenChanged, etc.) are generated
- ✅ Property preservation allows custom attributes
- ⚠️ Some property names don't match AD schema (phone, office)
- ⚠️ Missing some standard AD attributes (primaryGroupID, groupType, cn, etc.)
- ⚠️ Manager format is incorrect (should be DN)

### Impact on CSVDE Export
The current implementation will:
- ✅ Export successfully (no errors)
- ⚠️ Have some empty columns (Department, Company on real AD)
- ⚠️ Have incorrect phone/office property names
- ⚠️ Missing some expected AD attributes

### Recommended Action
Update `Convert-DataToADObjects` to add:
1. Standard AD attributes (cn, instanceType, primaryGroupID, groupType, objectCategory)
2. Correct property name mappings (telephoneNumber, mobile, physicalDeliveryOfficeName)
3. Manager DN format conversion

This will ensure full AD/CSVDE compatibility! 🎯
