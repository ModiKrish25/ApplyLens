"""
Resume proofreader — typos, date consistency, and tense mixing.

Classic rule-based NLP: every finding is shown with the exact quoted text,
where it appears, and why it's flagged. No black box.
"""

import re
from collections import defaultdict

from .parser import parse_experience

# ----------------------------------------------------------------- dictionary
# Common resume words the spell check must know, plus general English.
# A small, curated set keeps false positives low without a full dictionary.
KNOWN = set("""
a about above accomplish accomplished achieve achieved achievement achievements across action
actions adapt adapted add added address adjust admire adopt advanced advantage advertise advice
advising advisor advocate agile aim aligned alignment allocate allow allowed almost alone along
already also although always amazing among amount analysis analyst analyze analyzed and annual
another answer anticipate any anyone anything api apis appear applied apply applying approach
architecture architect architected area areas around as assess assessed asset assign assist
assisted associate at atmosphere attach attention audit augment author authority automate
automated automating autonomous available average avoid award awarded aware away backend back
background balance banking base based basic basics beauty because become been before begin
behaviour behind believe belong benchmark best better between beyond big bill billion build
builder building built business businesses busy but buy by cache caching calculate calculated
call called campaign campus can candidate capability cap capacity capital career care carry case
cash cast catalog category cause cell center central century certain chain challenge challenge
champion change changed channel chapter character charge chart chase cheap check checked chief
choice choose chosen circuit circulate cite citizen city civil claim class classic clean clear
client clients climate climb close cloud club cluster co code coded coding collaborate
collaborated collaboration colleague collect collected college column combination combine come
comfortable command comment commercial commit commitment common communicate communication
community compact company compare compared comparison compete competition compile complete
completed completely complex compliance comply compose compute computed computer computing
concept concepts concern conclude condition conduct conference confidence confident configure
confirm conflict confront confuse connect connected connection conscious consensus consent
consequence conserve consider considered consistent constant construct consult consume consumer
contact contain container content contest context continue contract contrast contribute
contributed contribution control convention conversation convert convinced cooperate coordinate
cope copy core corner corporate correct cost council count counterpart country county couple
course cover coverage create created creating creation creative credibility crisis criteria
critic critical criticism crop cross culture curious currency current currently customer
customers cut cycle daily damage data database databases date daughter day dead deal dear death
debate debt decade decide decision decline deep defend define defined degree delay delegate
deliberate deliver delivered delivery demand demonstration department depend dependent deployed
deploying deployment depth describe described description desert design designed designer
desirable desire desk despite destination destroy detail detailed detect determine develop
developed developing development device devote diagram dialogue die differ difference different
difficult digital dinner direct direction director discipline discover discuss discussion disease
dish dismiss display dispute distance distinct distribute distribution diverse divide division
do doctor document documented documentation does dollar domain domestic dominate done door double
doubt down download draft draw draw dream dress drink drive driver drop due duty dynamic each
eager early earn earned earth easily east easy eat economic economy edge edition editor educate
education effect effective efficiently effort egg eight either elaborate elastic elect electric
electronic element eligible eliminate else elsewhere embrace emerge emission emotion emphasis
empire employ employee employer employment empty enable enacted encounter encourage end endless
endorse endure energy enforce engage engagement engineer engineered engineering engineers english
enhance enhanced enough ensure enter enterprise entire entrance entry environment envision equal
equally equipment equivalent error errors escape especially essay essential establish estate
estimate ethics ethnic evaluate evaluation even evening event eventually ever every everyone
everything evidence evolve exact examine example excellent except exchange excite exclude excuse
execute exercise exhaust exhibit exist existence existing expand expansion expect expected
expedition expense experience experienced experiment expert explain explain explore export expose
express expression extend extension external extra fabric facility factor factory fail faint
fair faith fall false familiar family famous fancy fantasy fashion fast father fault favor fear
feasible feature february federal feed feel female festival fetch fever few fiber field fifteen
fifty fight figure file fill film final finally finance financial find fine finger finish firm
first fiscal fish fit five fix fixed flat flavor fleet flight float floor flow flower focus fold
folder follow following food fool foot for foreign forest forever forget form formal formation
former forward foster found foundation four fraction framework free freeze frequency frequent
fresh friend from front frozen fruit fuel full fun function functional fund fundamental funeral
funny furniture further future gain gallery game gap garage garden gas gate gather general
generate generated generation generous genetic genius gentle gentleman genuine get gift girl give
given glad glance glass global glory goal goals goes gold golf good govern government grab grace
grade gradually graduate grand grant graph graphic great greatest green grocery ground group grow
growing growth guarantee guard guess guest guide guideline guilt gun guy gym habit hair half hall
hand handle handling hang happen happy hard hardly harm hat hate have he head headline health
hear heart heat heavy held hello help helpful hence here heritage hero hesitate hey hidden high
highlight highly hike hill hint hire his history hit hold hole holiday hollow home honest honey
honor hope horizon horn horrible horse hospital host hot hotel hour house how however huge human
humble humor hundred hunger hungry hunt hurt husband hypothesis i ice idea ideal identify
identity ideology ignore ill illegal illness illustrate image imagination imagine immediate
immense immigrant impact implement implementation imply import impose impress impression improve
improved improvement impulse in incentive inch incident include included including income
increase increased increasing incredible indeed independence independent index indicate
indication indifferent individual industrial industry infant infection influence inform
information infrastructure ingredient initial initially initiate initiative inject injury inner
innocent innovation innovative input inquiry inside insight insist inspect inspire install
instance instead institute instruct instruction instrument insurance intellectual intelligence
intend intense interact interest interested interesting internal international internet
interpret interrupt interval interview into introduce introduction invade invent invest
investigate investigation investment invisible invite involve involved iron ironic is island
issue it item its itself jacket jail jam january jazz jealous jeans jet job join joint joke
journal journey joy judge juice jump june junior just justice justify keep key keyboard kick kid
kill kind king kitchen knee knife knock know knowledge known lab label labor lack ladder lake
land landscape lane language large largely last late later laugh launch laundry law lawn lawyer
lay layer lead leader leadership leading league learn learned learning least leather leave lecture
left leg legacy legal legend legislate legitimate leisure lemon lend length lesson let letter
level liberal library license lie life lift light like likely limit limited line link lion lip
liquid list listen literature lit little live lived living load loan local locate lock long
look lose loss lost lot loud love low lower loyal luck lucky lunch machine machines macro made
magic mail main maintain maintained maintenance major majority make maker makeup male mall
manage managed management manager managing mandate manner manufacture manufacturer many map
margin mark market marketing marriage marry mass master match mate material math matter maximum
may maybe mayor me meal mean meaning measure measurement meat mechanism media medical medicine
meet meeting member memory mental mention mentor menu merchandise mercy mere message metal
method metric middle might migrate mild military milk million mind mine mineral minimal minimize
minimum minister minor minute mirror miss missile mission mistake mix mixed mixture mobile mode
model modern modest modify moment monday money monitor month mood moral more morning mortgage
most mother motivation motor mount mountain mouse mouth move movie much mud multiply murder
muscle museum music mutual myself mystery myth nail name napkin narrow nation native nature
naughty near nearly necessary neck need negative neglect negotiate neighbor neither nephew nerve
nervous nest net network neutral never new news newspaper next nice niece night nine nobody nod
noise nominate none noon nor normal north nose not note nothing notice notion novel now nowhere
nuclear number nurse nut object objective obligation observe obtain obvious occasion occupy occur
ocean october odd odds off offer offered office officer official often oh oil ok okay old
olympic omit on once one onion online only onto open opening operate operation opinion opponent
opportunity oppose opposite option orange orchestra order ordinary organ organic organization
organize oriented origin original other others otherwise ought our ourselves out outcome outside
over overall overcome overlook owe own owner oxygen pace pack package page pain painful paint
pair palace pale palm pan panel paper paragraph parallel parcel pardon parent park parliament
parrot part participate particular partly partner party pass passage passenger passion past
patent path patience patient patrol pattern pause pay payment peace peak pen penalty pencil
people pepper per percent perceive perfect perform performance performed perhaps period
permanent permission permit person personal personality perspective persuade pet phase
philosophy phone photo phrase physical piano pick picture pie piece pierce pig pigeon pile pilot
pin pine pink pint pioneer pipe pitch pity pizza place plague plain plan plane planet planning
plant plastic plate platform play player plea please pleasure plenty plot plug plus pocket poem
poet point poison poke pole police policy polish polite political pollution ponder pool poor pop
popular population porch port portion portrait position positive possess possible possibly post
potato potential potentially pound pour poverty power practical practice practice praise pray
precise predict prefer pregnancy prepare presence present preserve president press pressure
pretty prevent previous price pride priest primary prime prince princess principal principle
print prior priority prison private prize probably problem procedure proceed process produce
product production profession professional professor profile profit program programmer progress
project prominent promise promote prompt proof proper property proportion proposal propose
prospect protect protection protein proud prove provide provided province psychology public
publish pull punch pupil purchase pure purpose pursue push put puzzle pyramid qualification
qualify quality quarter queen question queue quick quickly quiet quilt quit quite quiz quote
race rack radar radio rail rain raise rally random range rank rapid rare rarely rate rather
rating ratio reach react read reader ready real realize really reason reasonable recall receive
recent recently recipe recipe recite recognize recommend record recover recruit rectangle red
reduce reduced reducing refer reference reflect reform refuse regard regime region register
regret regular regulate rehearse reign reinforce reject relate related relative relax release
relevant reliable relief religion rely remain remark remedy remember remind remote removal remove
rent repair repeat replace reply report represent representative reputation request require
required requirement research resemble reservation reserve reside resign resist resolve resort
resource respect respond response responsibility responsible rest restaurant restore restrict
result resume retain retire retreat return reveal revenue review revise revolt reward rhythm
rice rich rid ride ring rise risk rival river road robot rock role roll roof room root rope rose
rotate rough round route routine row royal rub rubber rugby rule run runner running rural rush
rust sacred sad safe safety sage said sail saint salad salary sale sales salon salt same sample
sand satisfy saturday sauce save saving say scale scan scandal scared scatter scenario scene
schedule scheme scholar school science scientist score scrape screen screw script scroll
sculpture sea search season seat second secret section sector secure security see seed seek seem
segment seize seldom select selection self sell semester send senior sense sentence separate
sequence sergeant series serious serve service session set settle seven several severe shade
shadow shake shall shape share shark sharp she sheep sheet shelf shell shelter shift shine ship
shirt shiver shock shoe shoot shop shore short shortage shoulder shout show shower shut sick side
sight sign signal significant silence silent silicon silk silver similar simple simply sin since
sincere single sink sir sister sit site situation sixteen sixty size skate skill skilled skin
skirt sky slave sleep sleeve slice slide slight slightly slip slogan slope slow small smart smile
smoke smooth snack snake snow so soap soccer social society sock software soil solar soldier
solid solution solve some somebody somehow someone something sometimes somewhat son song soon
sorry sort soul sound soup source south space spare spark speak speaker special specialist
species specific specifically speech speed spell spend spent sphere spice spin spirit split
spoke sport spot spread spring square squeeze stable staff stage stain stair stake stale stamp
stand standard star stare start state statement station status stay steady steak steal steam
steel steep stem step stereo stick stiff still stir stock stomach stone stool stop storage store
storm story straight strain strait strange stranger strategy stream street strength stress
stretch strict strike string strip stroke strong strongly structure struggle student studio study
stuff stumble style subject submit subscribe substance substantial succeed success such sudden
suffer sufficient sugar suggest suggestion suit suitable sum summer summit sun super supply
support suppose sure surface surge surgeon surplus surprise surrender surround survey survive
suspect suspend sustain swallow swear sweat sweater sweep sweet swell swift swim swing switch
symbol sympathy symptom syndrome system table tablet tackle tail take tale talent talk tall tank
tap tape target task taste tattoo tax taxi tea teach teacher team tear tease tech technical
technique technology teeth telephone television tell temperature temple temporary ten tenant
tend tender tennis tension tent term terrible territory terror test text than thank that the
theater their them theme then theory therapy there therefore these they thick thief thin thing
think third thirst thirteen thirty this thorough those though thought thousand thread threat
three throat through throughout throw thumb thunder thursday thus ticket tide tidy tie tiger
tight till timber time tiny tip tired tissue title to tobacco today toe together toilet token
tomorrow tone tongue tonight too tool tooth top topic topple torch tornado torture total touch
tough tour tourist toward towel tower town toy trace track trade tradition traffic tragedy trail
train trait transaction transfer transform transition translate transparent transport trap
travel treasure treat treatment tree tremble trend trial triangle tribe trick trigger trim trip
triumph trolley troop trophy tropical trouble truck true truly trumpet trust truth try tube
tuesday tug tunnel turkey turn twelve twenty twice twin twist two type typical ugly ultimate
umbrella unable uncle under undergo understand understanding unemployment unfair unfold uniform
unify union unique unit united unity universe university unless unlike until unusual up update
upgrade uphold upon upper upset urge us usage use used useful user usual usually utility utterly
vacant vacation vaccine vacuum vague valid valley value valve van vanilla vanish vapor variable
variety various vary vast vault vegetable vehicle veil venture venue verb verdict verse version
vertical very vessel veteran veto via viable vibrant vicious victim victory video view vigil
village vinegar violate violence violin virtual virtue virus visa visible vision visit visitor
visual vital vivid vocal voice void volcano volume voluntary volunteer vote vow voyage wage waist
wait wake walk wall want war warm warn warrant warrior wash waste watch water wave way weak
wealth weapon wear weather weave website wednesday week weigh weight weird welcome welfare well
west wet what wheat wheel when whenever where whereas whether which while whisper whistle white
who whole whom whose why wide widely widow width wife wild will win wind window wine wing winner
winter wire wisdom wise wish with within without witness wizard wolf woman wonder wood wool word
work worker working works workshop world worry worth would wound wrap write writer writing
written wrong wrote yacht yard year yell yellow yes yesterday yet yield you young your yours
youth zone
""".split())

TECH_EXTRA = set("""
aws gcp azure docker kubernetes kubernetes django flask fastapi react angular vue javascript
typescript postgresql mysql mongodb redis sqlite github gitlab jenkins terraform ansible linux
nginx pandas numpy tensorflow pytorch sklearn spark kafka hadoop airflow tableau powerbi excel
figma jira scrum kanban api graphql restful websocket oauth jwt html css sql nosql json xml
ci cd devops saas paas iaas sdk ide ide cli gui ux ui seo pdf docx csv erp crm saas mvp poc
kpi roi q1 q2 q3 q4 b2b b2c saas
""".split())

# Top non-word typos we can catch without a dictionary (visible, high-signal).
COMMON_TYPOS = {
    "recieve": "receive", "seperate": "separate", "occured": "occurred",
    "deployement": "deployment", "deployements": "deployments", "envirnoment": "environment",
    "successfull": "successful", "managment": "management", "developement": "development",
    "enviroment": "environment", "comittee": "committee", "achive": "achieve",
    "acheive": "achieve", "adress": "address", "comitted": "committed",
    "experiance": "experience", "knowlege": "knowledge", "responsability": "responsibility",
    "responsiblity": "responsibility", "oppurtunity": "opportunity", "opurtunity": "opportunity",
    "begining": "beginning", "beleive": "believe", "buisness": "business",
    "calender": "calendar", "colleague": "colleague", "comitted": "committed",
    "concious": "conscious", "definately": "definitely", "embarass": "embarrass",
    "existance": "existence", "familar": "familiar", "finaly": "finally",
    "foriegn": "foreign", "goverment": "government", "gaurd": "guard",
    "happend": "happened", "immediatly": "immediately", "independant": "independent",
    "intrest": "interest", "literture": "literature", "maintainance": "maintenance",
    "neccessary": "necessary", "noticable": "noticeable", "occassion": "occasion",
    "paralell": "parallel", "persistant": "persistent", "posession": "possession",
    "prefered": "preferred", "publically": "publicly", "recomend": "recommend",
    "refered": "referred", "relevent": "relevant", "religiouse": "religious",
    "rumour": "rumor", "sicne": "since", "succesful": "successful",
    "suprise": "surprise", "tommorow": "tomorrow", "threshhold": "threshold",
    "tounge": "tongue", "untill": "until", "wierd": "weird",
    "javascript": "JavaScript",  # casing
    "pyhton": "Python", "javascrip": "JavaScript", "sqlserver": "SQL Server",
    "aws": "AWS", "sql": "SQL", "api": "API", "api's": "APIs",
}

MONTHS = ("jan january february march april may june july august september october november december "
          "feb mar apr jun jul aug sep sept oct nov dec").split()
# index() must find every alias the date regex can emit, so keep this canonical order:
def _month_index(name):
    n = name.lower()[:4].rstrip('.')
    canonical = {'jan':'jan','feb':'feb','mar':'mar','apr':'apr','may':'may','jun':'jun',
                 'jul':'jul','aug':'aug','sep':'sep','sept':'sep','oct':'oct','nov':'nov','dec':'dec'}
    base = canonical.get(n[:4], canonical.get(n[:3]))
    return 'jan feb mar apr may jun jul aug sep oct nov dec'.split().index(base) if base else -1


def proofread(text):
    """
    Returns {typos: [...], dates: {...}, tense: {...}, findings: [human summary]}.
    Every finding carries a quoted snippet + location reason.
    """
    findings = []
    text = (text or "").strip()
    if not text:
        return {"typos": [], "dates": {}, "tense": {}, "findings": ["Nothing to check — document is empty."]}

    # ------------------------------------------------------------- 1. typos
    typos = []
    seen = set()
    for m in re.finditer(r"[A-Za-z][A-Za-z']+", text):
        w = m.group(0)
        low = w.lower()
        if low in seen or low in KNOWN or low in TECH_EXTRA:
            continue
        if low in COMMON_TYPOS:
            start = max(0, m.start() - 55)
            end = min(len(text), m.end() + 55)
            snippet = " ".join(text[start:end].split())
            typos.append({
                "word": w, "suggestion": COMMON_TYPOS[low], "snippet": snippet,
            })
            seen.add(low)
    if typos:
        findings.append(f"{len(typos)} spelling issue(s) found.")
    else:
        findings.append("No common misspellings detected (curated list, not a full dictionary).")

    # ------------------------------------------------------ 2. date consistency
    date_pat = re.compile(
        r"\b(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?(\d{2,4})"
        r"|(\d{1,2})/(\d{4})|(\d{4})\s*(?:-|–|—|to)\s*(\d{4}|present|current|now))",
        re.IGNORECASE)
    raw_dates = []
    for m in date_pat.finditer(text):
        start = max(0, m.start() - 45)
        end = min(len(text), m.end() + 45)
        raw_dates.append({"text": m.group(0), "snippet": " ".join(text[start:end].split())})
    date_info = {
        "found": len(raw_dates),
        "samples": raw_dates[:6],
        "future_ranges": [],
        "suspicious_gaps": [],
    }

    # future end dates (not 'Present')
    for m in re.finditer(
            r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?)(\d{4})"
            r"\s*(?:-|–|—|to)\s*((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?)?(\d{4})",
            text, flags=re.IGNORECASE):
        try:
            end_year = int(m.group(4))
            if end_year > 2027:  # clearly mistyped future year
                start = max(0, m.start() - 45)
                date_info["future_ranges"].append({
                    "range": m.group(0), "end_year": end_year,
                    "snippet": " ".join(text[start:m.end() + 45].split()),
                })
        except ValueError:
            pass
    if date_info["future_ranges"]:
        findings.append(f"{len(date_info['future_ranges'])} date range(s) end in a far-future year — likely a typo.")

    # month ordering within a range (e.g. 'Jan 2023 - May 2022')
    for m in re.finditer(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?(\d{4}|'\d{2})"
            r"\s*(?:-|–|—|to)\s*"
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?(\d{4}|'\d{2})\b",
            text, flags=re.IGNORECASE):
        m1, y1, m2, y2 = m.group(1), m.group(2), m.group(3), m.group(4)
        if m1.lower() == "may":  # 'may' is ambiguous (month vs modal verb)
            continue
        mi1, mi2 = _month_index(m1), _month_index(m2)
        def _year(y):
            y = y.replace("'", "")
            return 2000 + int(y) if len(y) == 2 else int(y)
        y1i, y2i = _year(y1), _year(y2)
        if y1i and y2i and (y2i, mi2) < (y1i, mi1):
            start = max(0, m.start() - 45)
            date_info["suspicious_gaps"].append({
                "range": m.group(0),
                "snippet": " ".join(text[start:m.end() + 45].split()),
            })
    if date_info["suspicious_gaps"]:
        findings.append(f"{len(date_info['suspicious_gaps'])} date range(s) end before they start.")

    # gaps between experience entries (month-level)
    entries = parse_experience(text)
    parsed = []
    for e in entries:
        m = re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?(\d{4})"
            r".*?"
            r"((jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?(\d{4})|present|current|now)",
            e["dates"], flags=re.IGNORECASE)
        if m:
            sm_i = _month_index(m.group(1))
            sy = int(m.group(2))
            if re.search(r"present|current|now", m.group(3), re.IGNORECASE):
                em_i, ey = 12, 2026
            else:
                em_i = _month_index(m.group(4))
                ey = int(m.group(5))
            if sm_i >= 0 and em_i >= 0:
                parsed.append((sy, sm_i, ey, em_i, e["title"] or "Role"))
    gaps = []
    for prev, nxt in zip(parsed, parsed[1:]):
        prev_end = prev[2] * 12 + prev[3]
        next_start = nxt[0] * 12 + nxt[1]
        if next_start - prev_end >= 12:
            gaps.append({"after": prev[4], "before": nxt[4], "months": next_start - prev_end})
    date_info["gaps"] = gaps
    if gaps:
        findings.append(f"{len(gaps)} gap(s) of 12+ months between experience entries — be ready to explain them.")

    if not raw_dates:
        findings.append("No recognizable date ranges found — recruiters look for them; consider adding month-year ranges.")

    # ------------------------------------------------------------- 3. tense mixing
    # within the experience section, bullets should consistently start with past
    # (older roles) or present (current role) verbs
    action_past = ("built developed designed implemented led created improved reduced increased "
                   "automated migrated optimized launched delivered architected managed owned "
                   "drove spearheaded established").split()
    action_present = ("build develop design implement lead create improve reduce increase automate "
                      "migrate optimize launch deliver architect manage own drive spearhead "
                      "establish").split()
    sections = {}
    from .parser import split_sections
    sections = split_sections(text)
    exp_text = sections.get("experience", "")
    tense_info = {"past_bullets": 0, "present_bullets": 0, "mixed_lines": []}
    if exp_text:
        for line in exp_text.splitlines():
            line = line.strip(" \t•-*–")
            if not line or len(line) < 12:
                continue
            first = line.split()[0].lower().strip(",.()") if line.split() else ""
            if first in action_past:
                tense_info["past_bullets"] += 1
            elif first in action_present:
                tense_info["present_bullets"] += 1
        total = tense_info["past_bullets"] + tense_info["present_bullets"]
        if total >= 4 and tense_info["past_bullets"] and tense_info["present_bullets"]:
            findings.append(
                f"Mixed tense in Experience: {tense_info['past_bullets']} past-tense and "
                f"{tense_info['present_bullets']} present-tense bullets. (Tip: past roles → past tense; "
                f"current role → present tense.)")
        elif total >= 4:
            findings.append("Experience bullets use consistent tense — nice.")
    else:
        findings.append("No Experience section detected — tense check skipped.")

    return {"typos": typos, "dates": date_info, "tense": tense_info, "findings": findings}
