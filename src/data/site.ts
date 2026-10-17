export const site = {
  name: "Turnmark",
  title: "Swim Time Converter: SCY, SCM & LCM | Turnmark",
  url: "https://stanback.github.io/turnmark/",
  description:
    "Convert swim times between yards and meters (SCY, SCM, LCM). Compare USA Swimming and USMS standards, calculate World Aquatics points, and adjust for altitude.",
};
export const faqs = [
  {
    question: "How do I convert swim times between yards and meters?",
    answer:
      "Choose your stroke, distance, entered time, and the course you swam. Turnmark shows estimates for SCY, SCM, and LCM using NCAA metric-to-yards factors. Reverse conversions and meter-to-meter comparisons are derived from those published factors. Unsupported conversions stay unavailable.",
    url: "https://ncaaorg.s3.amazonaws.com/championships/sports/swimdive/rules/PRXSW_RulesBook.pdf#page=125",
    source: "NCAA conversion tables",
  },
  {
    question: "What do SCY, SCM, and LCM mean?",
    answer:
      "SCY means short course yards, a 25-yard pool. SCM means short course meters, a 25-meter pool. LCM means long course meters, a 50-meter pool. Freestyle distances of 500, 1000, and 1650 yards map to 400, 800, and 1500 meters respectively; other supported events retain their numerical distance.",
  },
  {
    question: "Can I adjust a swim time for altitude?",
    answer:
      "Yes. Enter the pool elevation in feet or meters. For eligible events of 200 or longer at 3,000 ft (914.4 m) or above, Turnmark subtracts the USA Swimming altitude adjustment before converting courses. The result is labeled as a sea-level estimate. Your actual swim and the deduction remain visible. Meet rules determine whether an adjustment is accepted.",
    url: "https://www.usaswimming.org/docs/default-source/timesdocuments/general-docs/times-and-recognition-policy-manual.pdf#page=7",
    source: "USA Swimming altitude policy",
  },
  {
    question: "Which swim time standards can I compare against?",
    answer:
      "The standards selector includes USA Swimming’s 2024–2028 youth motivational ladder and the published 2026 U.S. Masters Swimming National Qualifying Times for adults. USMS targets cover SCY and LCM, with age groups from 18–24 through 80–84; USMS does not set NQTs for ages 85+. Missing targets are left blank. These two datasets serve different purposes; the adult view does not invent B–AAAA levels.",
    url: "https://www.usms.org/events/national-championships/pool-national-championships/national-qualifying-times",
    source: "USMS national qualifying times",
  },
  {
    question: "How are World Aquatics points calculated?",
    answer:
      "World Aquatics points use 1,000 × (base time / swim time)³, truncated to a whole number. The base time is the world-record reference for that event, course, and category at the table’s cutoff date; matching it earns 1,000 points. Turnmark uses the published 2026 tables for entered SCM and LCM swims, without altitude or age adjustment. The next points target is the next multiple of 100 above your score, with a calculated time to aim for. It is a suggested goal, not an official qualifying time. Yards swims are left unscored.",
    url: "https://www.worldaquatics.com/swimming/points",
    source: "World Aquatics scoring method",
  },
  {
    question: "Are converted times official qualifying times?",
    answer:
      "Course conversions are estimates, not official swims. Entry eligibility depends on the specific meet’s rules, qualifying window, accepted courses, and adjustment policies. A displayed standard comparison does not confirm eligibility. Check the published meet information before submitting an entry.",
  },
  {
    question: "Can I install Turnmark and use it offline?",
    answer:
      "Yes. Supported browsers can install Turnmark as an app with its own icon and window. In Chrome, use the install option in the address bar or browser menu. On iPhone or iPad, use Safari’s Share menu and Add to Home Screen. Once the app files have been cached after an online visit, the converter and bundled standards work offline. External source links require a connection.",
  },
  {
    question: "Where are my conversion history and saved swims stored?",
    answer:
      "Your last 50 conversions and up to eight saved swims stay in this browser’s local storage. There is no account, cloud sync, analytics, or upload of swim data. You can remove individual conversions or clear your history. Clearing browser site data removes these local records. A shared link includes the swim details encoded in its URL fragment.",
  },
];
