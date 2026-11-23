// Cloudflare Pages Function - /api/public/students
// Guarantees instant 10ms response for student list dropdowns across all 10 classes
const ALL_STUDENTS = {
  "1s1": [
    {
      "id": 215,
      "username": "oussama.majri.listee",
      "full_name": "Oussama Majri (أسامة ماجري)",
      "classe": "1s1"
    },
    {
      "id": 216,
      "username": "amir.hamdi.listee",
      "full_name": "Amir Hamdi (أمير حمدي)",
      "classe": "1s1"
    },
    {
      "id": 217,
      "username": "oumayma.nasri.listee",
      "full_name": "Oumayma Nasri (أميمة نصري)",
      "classe": "1s1"
    },
    {
      "id": 218,
      "username": "aya.krichi.listee",
      "full_name": "Aya Krichi (آية كريشي)",
      "classe": "1s1"
    },
    {
      "id": 219,
      "username": "ines.hamdi.listee",
      "full_name": "Ines Hamdi (إيناس حمدي)",
      "classe": "1s1"
    },
    {
      "id": 220,
      "username": "ayoub.mbareki.listee",
      "full_name": "Ayoub Mbareki (أيوب مباركي)",
      "classe": "1s1"
    },
    {
      "id": 221,
      "username": "hamza.adali.listee",
      "full_name": "Hamza Adali (حمزة عدالي)",
      "classe": "1s1"
    },
    {
      "id": 222,
      "username": "khloud.dhouioui.listee",
      "full_name": "Khloud Dhouioui (خلود الضويوي)",
      "classe": "1s1"
    },
    {
      "id": 223,
      "username": "ritaj.thabti.listee",
      "full_name": "Ritaj Thabti (ريتاج ثابتي)",
      "classe": "1s1"
    },
    {
      "id": 224,
      "username": "riad.nasraoui.listee",
      "full_name": "Riad Nasraoui (رياض نصراوي)",
      "classe": "1s1"
    },
    {
      "id": 225,
      "username": "rayan.belhoudi.listee",
      "full_name": "Rayan Belhoudi (ريان بلحودي)",
      "classe": "1s1"
    },
    {
      "id": 226,
      "username": "zeineb.cherif.listee",
      "full_name": "Zeineb Cherif (زينب الشريف)",
      "classe": "1s1"
    },
    {
      "id": 227,
      "username": "sirine.omrani.listee",
      "full_name": "Sirine Omrani (سيرين العمراني)",
      "classe": "1s1"
    },
    {
      "id": 228,
      "username": "senda.mahfoudhi.listee",
      "full_name": "Senda Mahfoudhi (سندة محفوظي)",
      "classe": "1s1"
    },
    {
      "id": 229,
      "username": "chaima.tlili.listee",
      "full_name": "Chaima Tlili (شيماء تليلي)",
      "classe": "1s1"
    },
    {
      "id": 230,
      "username": "abir.hamdi.listee",
      "full_name": "Abir Hamdi (عبير حمدي)",
      "classe": "1s1"
    },
    {
      "id": 231,
      "username": "ghaith.chehibi.listee",
      "full_name": "Ghaith Chehibi (غيث شهيبي)",
      "classe": "1s1"
    },
    {
      "id": 232,
      "username": "fatma.thabti.listee",
      "full_name": "Fatma Thabti (فاطمة ثابتي)",
      "classe": "1s1"
    },
    {
      "id": 233,
      "username": "mohamed.thabti.listee",
      "full_name": "Mohamed Thabti (محمد ثابتي)",
      "classe": "1s1"
    },
    {
      "id": 234,
      "username": "mohamed.omrani.listee",
      "full_name": "Mohamed أمين Omrani (محمد أمين العمراني)",
      "classe": "1s1"
    },
    {
      "id": 235,
      "username": "meriem.nasri.listee",
      "full_name": "Meriem Nasri (مريم نصري)",
      "classe": "1s1"
    },
    {
      "id": 236,
      "username": "maha.krichi.listee",
      "full_name": "Maha Krichi (مها كريشي)",
      "classe": "1s1"
    },
    {
      "id": 237,
      "username": "maya.omrani.listee",
      "full_name": "Maya Omrani (مية العمراني)",
      "classe": "1s1"
    },
    {
      "id": 238,
      "username": "naoures.dhouioui.listee",
      "full_name": "Naoures Dhouioui (نورس ضويوي)",
      "classe": "1s1"
    },
    {
      "id": 239,
      "username": "wiem.nasri.listee",
      "full_name": "Wiem Nasri (وئام نصري)",
      "classe": "1s1"
    },
    {
      "id": 240,
      "username": "yassine.dhouioui.listee",
      "full_name": "Yassine Dhouioui (ياسين ضويوي)",
      "classe": "1s1"
    },
    {
      "id": 241,
      "username": "yaqine.hamdi.listee",
      "full_name": "Yaqine Hamdi (ياقين حمدي)",
      "classe": "1s1"
    },
    {
      "id": 242,
      "username": "ayoub.omrani.listee",
      "full_name": "Ayoub Omrani (أيوب عمراني)",
      "classe": "1s1"
    },
    {
      "id": 243,
      "username": "maram.fakher.listee",
      "full_name": "Maram Fakher (مرام الفاخر)",
      "classe": "1s1"
    }
  ],
  "1s2": [
    {
      "id": 268,
      "username": "ibrahim.bachir.listeg",
      "full_name": "Ibrahim Bachir (إبراهيم بشير)",
      "classe": "1s2"
    },
    {
      "id": 269,
      "username": "azer.dhouioui.listeg",
      "full_name": "Azer Dhouioui (آزر ضويوي)",
      "classe": "1s2"
    },
    {
      "id": 270,
      "username": "israa.thabti.listeg",
      "full_name": "Israa Thabti (إسراء ثابتي)",
      "classe": "1s2"
    },
    {
      "id": 271,
      "username": "islam.sebri.listeg",
      "full_name": "Islam Sebri (إسلام سبري)",
      "classe": "1s2"
    },
    {
      "id": 272,
      "username": "islam.nasri.listeg",
      "full_name": "Islam Nasri (إسلام نصري)",
      "classe": "1s2"
    },
    {
      "id": 273,
      "username": "amir.meskini.listeg",
      "full_name": "Amir Meskini (أمير مسكيني)",
      "classe": "1s2"
    },
    {
      "id": 274,
      "username": "aya.fakher.listeg",
      "full_name": "Aya Fakher (آية الفاخر)",
      "classe": "1s2"
    },
    {
      "id": 275,
      "username": "aya.saanouni.listeg",
      "full_name": "Aya Saanouni (آية صعفوني)",
      "classe": "1s2"
    },
    {
      "id": 276,
      "username": "aya.nasri.listeg",
      "full_name": "Aya Nasri (آية نصري)",
      "classe": "1s2"
    },
    {
      "id": 277,
      "username": "belgacem.dhouioui.listeg",
      "full_name": "Belgacem Dhouioui (بلقاسم ضويوي)",
      "classe": "1s2"
    },
    {
      "id": 278,
      "username": "khloud.mahfoudhi.listeg",
      "full_name": "Khloud Mahfoudhi (خلود محفوظي)",
      "classe": "1s2"
    },
    {
      "id": 279,
      "username": "rym.hmida.listeg",
      "full_name": "Rym Hmida (ريتم حميدة)",
      "classe": "1s2"
    },
    {
      "id": 280,
      "username": "rym.hamdi.listeg",
      "full_name": "Rym Hamdi (ريتم حمدي)",
      "classe": "1s2"
    },
    {
      "id": 281,
      "username": "rita.hamdi.listeg",
      "full_name": "Rita Hamdi (ريتا حمدي)",
      "classe": "1s2"
    },
    {
      "id": 282,
      "username": "rayan.rahimi.listeg",
      "full_name": "Rayan Rahimi (ريان رحيمي)",
      "classe": "1s2"
    },
    {
      "id": 283,
      "username": "samar.sebri.listeg",
      "full_name": "Samar Sebri (سمر سبري)",
      "classe": "1s2"
    },
    {
      "id": 284,
      "username": "sanaa.belhoudi.listeg",
      "full_name": "Sanaa Belhoudi (سناء بلحودي)",
      "classe": "1s2"
    },
    {
      "id": 285,
      "username": "chahd.nasri.listeg",
      "full_name": "Chahd Nasri (شهد نصري)",
      "classe": "1s2"
    },
    {
      "id": 286,
      "username": "mlouki.listeg",
      "full_name": "Mlouki (ملوكي)",
      "classe": "1s2"
    },
    {
      "id": 287,
      "username": "chaima.belhoudi.listeg",
      "full_name": "Chaima Belhoudi (شيماء بلحودي)",
      "classe": "1s2"
    },
    {
      "id": 288,
      "username": "ali.slaoui.listeg",
      "full_name": "Ali Slaoui (علي سلاوي)",
      "classe": "1s2"
    },
    {
      "id": 289,
      "username": "ghaith.belhoudi.listeg",
      "full_name": "Ghaith Belhoudi (غيث بلحودي)",
      "classe": "1s2"
    },
    {
      "id": 290,
      "username": "firas.fakher.listeg",
      "full_name": "Firas Fakher (فراس الفاخر)",
      "classe": "1s2"
    },
    {
      "id": 291,
      "username": "majid.ali.rahmani.listeg",
      "full_name": "Majid Ali Rahmani (مجيد علي رحماني)",
      "classe": "1s2"
    },
    {
      "id": 292,
      "username": "maram.akremi.listeg",
      "full_name": "Maram Akremi (مرام عكرمي)",
      "classe": "1s2"
    },
    {
      "id": 293,
      "username": "meriem.hamdi.listeg",
      "full_name": "Meriem Hamdi (مريم حمدي)",
      "classe": "1s2"
    }
  ],
  "1s3": [
    {
      "id": 244,
      "username": "adem.merki.listef",
      "full_name": "Adem Merki (آدم المركي)",
      "classe": "1s3"
    },
    {
      "id": 245,
      "username": "rahmani.listef",
      "full_name": "أجل Rahmani (أجل رحماني)",
      "classe": "1s3"
    },
    {
      "id": 246,
      "username": "oumayma.rahmani.listef",
      "full_name": "Oumayma Rahmani (أميمة رحماني)",
      "classe": "1s3"
    },
    {
      "id": 247,
      "username": "missaoui.listef",
      "full_name": "خير الدين Missaoui (خير الدين ميساوي)",
      "classe": "1s3"
    },
    {
      "id": 248,
      "username": "ragheb.rahmani.listef",
      "full_name": "Ragheb Rahmani (راغب رحماني)",
      "classe": "1s3"
    },
    {
      "id": 249,
      "username": "ritaj.rahmani.listef",
      "full_name": "Ritaj Rahmani (رتاج رحماني)",
      "classe": "1s3"
    },
    {
      "id": 250,
      "username": "rym.dhouioui.listef",
      "full_name": "Rym Dhouioui (ريتم ضويوي)",
      "classe": "1s3"
    },
    {
      "id": 251,
      "username": "rym.meskini.listef",
      "full_name": "Rym Meskini (ريتم مسكيني)",
      "classe": "1s3"
    },
    {
      "id": 252,
      "username": "zeineb.rahmani.listef",
      "full_name": "Zeineb Rahmani (زينب رحماني)",
      "classe": "1s3"
    },
    {
      "id": 253,
      "username": "saja.ajroudi.listef",
      "full_name": "Saja Ajroudi (سجى العجرودي)",
      "classe": "1s3"
    },
    {
      "id": 254,
      "username": "salma.rahmani.listef",
      "full_name": "Salma Rahmani (سلمى رحماني)",
      "classe": "1s3"
    },
    {
      "id": 255,
      "username": "ali.sebri.listef",
      "full_name": "Ali Sebri (علي سبري)",
      "classe": "1s3"
    },
    {
      "id": 256,
      "username": "imed.saanouni.listef",
      "full_name": "Imed Saanouni (عماد صعفوني)",
      "classe": "1s3"
    },
    {
      "id": 257,
      "username": "omar.dhouioui.listef",
      "full_name": "Omar Dhouioui (عمر ضويوي)",
      "classe": "1s3"
    },
    {
      "id": 258,
      "username": "ghaith.andaoui.listef",
      "full_name": "Ghaith Andaoui (غيث عنداوي)",
      "classe": "1s3"
    },
    {
      "id": 259,
      "username": "farah.dhouioui.listef",
      "full_name": "Farah Dhouioui (فرح ضويوي)",
      "classe": "1s3"
    },
    {
      "id": 260,
      "username": "meriem.rahmani.listef",
      "full_name": "Meriem Rahmani (مريم رحماني)",
      "classe": "1s3"
    },
    {
      "id": 261,
      "username": "moataz.ghouila.listef",
      "full_name": "Moataz Ghouila (معتز غويلة)",
      "classe": "1s3"
    },
    {
      "id": 262,
      "username": "houda.dhouioui.listef",
      "full_name": "Houda Dhouioui (هدى ضويوي)",
      "classe": "1s3"
    },
    {
      "id": 263,
      "username": "wiem.thabti.listef",
      "full_name": "Wiem Thabti (وئام ثابتي)",
      "classe": "1s3"
    },
    {
      "id": 264,
      "username": "wiem.chehibi.listef",
      "full_name": "Wiem Chehibi (وئام شهيبي)",
      "classe": "1s3"
    },
    {
      "id": 265,
      "username": "yasmine.dhouioui.listef",
      "full_name": "Yasmine Dhouioui (ياسمين ضويوي)",
      "classe": "1s3"
    },
    {
      "id": 266,
      "username": "yasmine.ajbouli.listef",
      "full_name": "Yasmine Ajbouli (ياسمين عجبولي)",
      "classe": "1s3"
    },
    {
      "id": 267,
      "username": "yosr.dhouioui.listef",
      "full_name": "Yosr Dhouioui (يسر ضويوي)",
      "classe": "1s3"
    }
  ],
  "2 ECO": [
    {
      "id": 22,
      "username": "ahmd.syd",
      "full_name": "Ahmd Dhouyouy Syd (احمد ضويوي  سيد)",
      "classe": "2 ECO"
    },
    {
      "id": 23,
      "username": "adam.chehibi",
      "full_name": "Adam Chehibi (ادم الشهيبي)",
      "classe": "2 ECO"
    },
    {
      "id": 24,
      "username": "arij.adali",
      "full_name": "Arij Adali (اريج عدالي)",
      "classe": "2 ECO"
    },
    {
      "id": 25,
      "username": "amani.krichi",
      "full_name": "Amani Krichi (اماني كريشي)",
      "classe": "2 ECO"
    },
    {
      "id": 26,
      "username": "ayoub.belhoudi",
      "full_name": "Ayoub Belhoudi (ايويب بلحودي)",
      "classe": "2 ECO"
    },
    {
      "id": 27,
      "username": "ibtehal.meskini",
      "full_name": "Ibtehal Meskini (ابتهال مسكيني)",
      "classe": "2 ECO"
    },
    {
      "id": 28,
      "username": "hala.thabeti",
      "full_name": "Hala Thabeti (حلا ثابتي)",
      "classe": "2 ECO"
    },
    {
      "id": 29,
      "username": "rym.dhouioui",
      "full_name": "Rym Dhouioui (ريم ضويوي)",
      "classe": "2 ECO"
    },
    {
      "id": 30,
      "username": "rayan.dhouioui",
      "full_name": "Rayan Dhouioui (ريان ضويوي)",
      "classe": "2 ECO"
    },
    {
      "id": 31,
      "username": "zeineb.rahmani",
      "full_name": "Zeineb Rahmani (زينب رحماني)",
      "classe": "2 ECO"
    },
    {
      "id": 32,
      "username": "chaima.ellouzi",
      "full_name": "Chaima Ellouzi (شيماء اللوزي)",
      "classe": "2 ECO"
    },
    {
      "id": 33,
      "username": "ghofrane.thabeti",
      "full_name": "Ghofrane Thabeti (غفران ثابتي)",
      "classe": "2 ECO"
    },
    {
      "id": 34,
      "username": "fares.dhouioui",
      "full_name": "Fares Dhouioui (فارس ضويوي)",
      "classe": "2 ECO"
    },
    {
      "id": 35,
      "username": "maram.nasri",
      "full_name": "Maram Nasri (مرام نصري)",
      "classe": "2 ECO"
    },
    {
      "id": 36,
      "username": "meriem.rahmani",
      "full_name": "Meriem Rahmani (مريم رحماني)",
      "classe": "2 ECO"
    },
    {
      "id": 37,
      "username": "malek.briki",
      "full_name": "Malek Briki (ملاك بريكي)",
      "classe": "2 ECO"
    },
    {
      "id": 38,
      "username": "mayssa.dhouioui",
      "full_name": "Mayssa Dhouioui (ميساء ضويوي)",
      "classe": "2 ECO"
    },
    {
      "id": 39,
      "username": "nadine.thabeti",
      "full_name": "Nadine Thabeti (نادين ثابتي)",
      "classe": "2 ECO"
    },
    {
      "id": 40,
      "username": "nermine.nasri",
      "full_name": "Nermine Nasri (نرمين نصري)",
      "classe": "2 ECO"
    },
    {
      "id": 41,
      "username": "nour.rahmani",
      "full_name": "Nour El Houda Rahmani (نور الهدى رحماني)",
      "classe": "2 ECO"
    },
    {
      "id": 42,
      "username": "yasmine.hamdi",
      "full_name": "Yasmine Hamdi (ياسمين حمدي)",
      "classe": "2 ECO"
    },
    {
      "id": 43,
      "username": "yahya.thabeti",
      "full_name": "Yahya Thabeti (يحي ثابتي)",
      "classe": "2 ECO"
    },
    {
      "id": 44,
      "username": "raed.saanouni",
      "full_name": "Raed Saanouni (رائد صعنوني)",
      "classe": "2 ECO"
    },
    {
      "id": 45,
      "username": "hadeel.sebri",
      "full_name": "Hadeel Sebri (هديل سبري)",
      "classe": "2 ECO"
    },
    {
      "id": 46,
      "username": "ahmed.habib",
      "full_name": "Ahmed Dhouioui Habib (احمد ضويوي حبيب)",
      "classe": "2 ECO"
    }
  ],
  "2 IT": [
    {
      "id": 47,
      "username": "adam.hamdi",
      "full_name": "Adam Hamdi (ادم حمدي)",
      "classe": "2 IT"
    },
    {
      "id": 48,
      "username": "jihane.oa",
      "full_name": "Jihane Ouled Ahmed (جيهان اولاد احمد)",
      "classe": "2 IT"
    },
    {
      "id": 49,
      "username": "rym.majri",
      "full_name": "Rym Majri (ريم ماجري)",
      "classe": "2 IT"
    },
    {
      "id": 50,
      "username": "rayan.nasri",
      "full_name": "Rayan Nasri (ريان نصري)",
      "classe": "2 IT"
    },
    {
      "id": 51,
      "username": "zeineb.guizani",
      "full_name": "Zeineb Guizani (زينب قيزاني)",
      "classe": "2 IT"
    },
    {
      "id": 52,
      "username": "abderrahmane.h",
      "full_name": "Abderrahmane Harki (عبد الرحمان حاركي)",
      "classe": "2 IT"
    },
    {
      "id": 53,
      "username": "abderrahmane.r",
      "full_name": "Abderrahmane Rahmani (عبد الرحمان رحماني)",
      "classe": "2 IT"
    },
    {
      "id": 54,
      "username": "omar.dhouioui",
      "full_name": "Omar Dhouioui (عمر ضويوي)",
      "classe": "2 IT"
    },
    {
      "id": 55,
      "username": "fatma.khemari",
      "full_name": "Fatma Khemari (فاطمة خماري)",
      "classe": "2 IT"
    },
    {
      "id": 56,
      "username": "moataz.thabeti",
      "full_name": "Moataz Thabeti (معتز ثابتي)",
      "classe": "2 IT"
    },
    {
      "id": 57,
      "username": "yasmine.dhouioui",
      "full_name": "Yasmine Dhouioui (ياسمين ضويوي)",
      "classe": "2 IT"
    },
    {
      "id": 58,
      "username": "yasmina.belhoudi",
      "full_name": "Yasmina Belhoudi (ياسمينة بلحودي)",
      "classe": "2 IT"
    },
    {
      "id": 59,
      "username": "youssef.nasri",
      "full_name": "Youssef Nasri (يوسف نصري)",
      "classe": "2 IT"
    },
    {
      "id": 60,
      "username": "nour.meskini",
      "full_name": "Nour Meskini (نور مسكيني)",
      "classe": "2 IT"
    }
  ],
  "2 Lettre": [
    {
      "id": 294,
      "username": "islam.krichi",
      "full_name": "Islam Krichi (إسلام كريشي)",
      "classe": "2 Lettre"
    },
    {
      "id": 295,
      "username": "achraf.akremi",
      "full_name": "Achraf Akremi (أشرف عكرمي)",
      "classe": "2 Lettre"
    },
    {
      "id": 296,
      "username": "ilyes.tlili",
      "full_name": "Ilyes Tlili (إلياس تليلي)",
      "classe": "2 Lettre"
    },
    {
      "id": 297,
      "username": "basma.dhouioui",
      "full_name": "Basma Dhouioui (بسمة ضويوي)",
      "classe": "2 Lettre"
    },
    {
      "id": 298,
      "username": "hamza.nasri",
      "full_name": "Hamza Nasri (حمزة نصري)",
      "classe": "2 Lettre"
    },
    {
      "id": 299,
      "username": "khalil.ajbouni",
      "full_name": "Khalil Ajbouni (خليل عجبوني)",
      "classe": "2 Lettre"
    },
    {
      "id": 300,
      "username": "dheker.chehibi",
      "full_name": "Dheker Chehibi (ذاكر شهيبي)",
      "classe": "2 Lettre"
    },
    {
      "id": 301,
      "username": "rahma.hamdi",
      "full_name": "Rahma Hamdi (رحمة حمدي)",
      "classe": "2 Lettre"
    },
    {
      "id": 302,
      "username": "zeineb.chbitli",
      "full_name": "Zeineb Chbitli (زينب شبيطلي)",
      "classe": "2 Lettre"
    },
    {
      "id": 303,
      "username": "chaima.mlouki",
      "full_name": "Chaima Mlouki (شيماء ملوكي)",
      "classe": "2 Lettre"
    },
    {
      "id": 304,
      "username": "salah.alimi",
      "full_name": "Salah Alimi (صالح عليمي)",
      "classe": "2 Lettre"
    },
    {
      "id": 305,
      "username": "safia.dhouioui",
      "full_name": "Safia Dhouioui (صفية ضويوي)",
      "classe": "2 Lettre"
    },
    {
      "id": 306,
      "username": "karima.dhouioui",
      "full_name": "Karima Dhouioui (كريمة ضويوي)",
      "classe": "2 Lettre"
    },
    {
      "id": 307,
      "username": "nabil.jebnouni",
      "full_name": "Nabil Jebnouni (نبيل جبنوني)",
      "classe": "2 Lettre"
    },
    {
      "id": 308,
      "username": "nourimen.akremi",
      "full_name": "Nour Imen Akremi (نور إيمان عكرمي)",
      "classe": "2 Lettre"
    },
    {
      "id": 309,
      "username": "yosra.khemari",
      "full_name": "Yosra Khemari (يسرى خماري)",
      "classe": "2 Lettre"
    },
    {
      "id": 310,
      "username": "yosra.kbari",
      "full_name": "Yosra Kbari (يسرى كباري)",
      "classe": "2 Lettre"
    },
    {
      "id": 311,
      "username": "youssef.saanouni",
      "full_name": "Youssef Saanouni (يوسف صعنوني)",
      "classe": "2 Lettre"
    }
  ],
  "2 science": [
    {
      "id": 117,
      "username": "adem.omrani",
      "full_name": "Adem Omrani (آدم العمراني)",
      "classe": "2 science"
    },
    {
      "id": 118,
      "username": "adem.thabti",
      "full_name": "Adem Thabti (آدم ثابتي)",
      "classe": "2 science"
    },
    {
      "id": 119,
      "username": "aya.rahmani",
      "full_name": "Aya Rahmani (آية رحماني)",
      "classe": "2 science"
    },
    {
      "id": 120,
      "username": "roua.saanouni",
      "full_name": "Roua Saanouni (رؤى صعنوني)",
      "classe": "2 science"
    },
    {
      "id": 121,
      "username": "dhouha.nasri",
      "full_name": "Dhouha Nasri (ضحى نصري)",
      "classe": "2 science"
    },
    {
      "id": 122,
      "username": "dhia.rahimi",
      "full_name": "Dhia Rahimi (ضياء رحيمي)",
      "classe": "2 science"
    },
    {
      "id": 123,
      "username": "abir.nasraoui",
      "full_name": "Abir Nasraoui (عبير نصراوي)",
      "classe": "2 science"
    },
    {
      "id": 124,
      "username": "aziz.omrani",
      "full_name": "Aziz Omrani (عزيز العمراني)",
      "classe": "2 science"
    },
    {
      "id": 125,
      "username": "farah.thabti",
      "full_name": "Farah Thabti (فرح ثابتي)",
      "classe": "2 science"
    },
    {
      "id": 126,
      "username": "mohamed.krichi",
      "full_name": "Mohamed Krichi (محمد كريشي)",
      "classe": "2 science"
    },
    {
      "id": 127,
      "username": "mohamedaziz.helali",
      "full_name": "Mohamed Aziz Helali (محمد عزيز هلالي)",
      "classe": "2 science"
    },
    {
      "id": 128,
      "username": "mohamedamine.meskini",
      "full_name": "Mohamed Amine Meskini (محمد أمين مسكيني)",
      "classe": "2 science"
    },
    {
      "id": 129,
      "username": "meriem.rahmani.sc",
      "full_name": "Meriem Rahmani (مريم رحماني)",
      "classe": "2 science"
    },
    {
      "id": 130,
      "username": "nesrine.dhouioui",
      "full_name": "Nesrine Dhouioui (نسرين ضويوي)",
      "classe": "2 science"
    },
    {
      "id": 131,
      "username": "youssef.nasri.sc",
      "full_name": "Youssef Nasri (يوسف نصري)",
      "classe": "2 science"
    }
  ],
  "3eco": [
    {
      "id": 188,
      "username": "adem.nasri.listed",
      "full_name": "Adem Nasri (آدم نصري)",
      "classe": "3eco"
    },
    {
      "id": 189,
      "username": "alaa.dhouioui.listed",
      "full_name": "Alaa Dhouioui (ألاء ضويوي)",
      "classe": "3eco"
    },
    {
      "id": 190,
      "username": "amani.dhouioui.listed",
      "full_name": "Amani Dhouioui (أماني ضويوي)",
      "classe": "3eco"
    },
    {
      "id": 191,
      "username": "iheb.nasri.listed",
      "full_name": "Iheb Nasri (إيهاب نصري)",
      "classe": "3eco"
    },
    {
      "id": 192,
      "username": "zeineb.belhoudi.listed",
      "full_name": "Zeineb Belhoudi (زينب بلحودي)",
      "classe": "3eco"
    },
    {
      "id": 193,
      "username": "rahmani.listed",
      "full_name": "Rahmani (رحماني)",
      "classe": "3eco"
    },
    {
      "id": 194,
      "username": "zeineb.dhouioui.listed",
      "full_name": "Zeineb Dhouioui (زينب ضويوي)",
      "classe": "3eco"
    },
    {
      "id": 195,
      "username": "nasraoui.listed",
      "full_name": "عبد الله Nasraoui (عبد الله نصراوي)",
      "classe": "3eco"
    },
    {
      "id": 196,
      "username": "ezzeddine.hamdi.listed",
      "full_name": "Ezzeddine Hamdi (عزالدين حمدي)",
      "classe": "3eco"
    },
    {
      "id": 197,
      "username": "ghanem.omrani.listed",
      "full_name": "Ghanem Omrani (غانم العمراني)",
      "classe": "3eco"
    },
    {
      "id": 198,
      "username": "ghofrane.nasri.listed",
      "full_name": "Ghofrane Nasri (غفران نصري)",
      "classe": "3eco"
    },
    {
      "id": 199,
      "username": "fatma.hamdi.listed",
      "full_name": "Fatma Hamdi (فاطمة الحمدي)",
      "classe": "3eco"
    },
    {
      "id": 200,
      "username": "majed.mlouki.listed",
      "full_name": "Majed Mlouki (ماجد ملوكي)",
      "classe": "3eco"
    },
    {
      "id": 201,
      "username": "mohamed.aziz.nasraoui.listed",
      "full_name": "Mohamed Aziz Nasraoui (محمد عزيز نصراوي)",
      "classe": "3eco"
    },
    {
      "id": 202,
      "username": "mohamed.louay.nasri.listed",
      "full_name": "Mohamed Louay Nasri (محمد لؤي نصري)",
      "classe": "3eco"
    },
    {
      "id": 203,
      "username": "maram.rahmani.listed",
      "full_name": "Maram Rahmani (مرام رحماني)",
      "classe": "3eco"
    },
    {
      "id": 204,
      "username": "malek.rahmani.listed",
      "full_name": "Malek Rahmani (ملاك رحماني)",
      "classe": "3eco"
    },
    {
      "id": 205,
      "username": "malek.nasraoui.listed",
      "full_name": "Malek Nasraoui (ملاك نصراوي)",
      "classe": "3eco"
    },
    {
      "id": 206,
      "username": "mounir.dridi.listed",
      "full_name": "Mounir Dridi (منير الدريدي)",
      "classe": "3eco"
    },
    {
      "id": 207,
      "username": "cherif.listed",
      "full_name": "نور الصباح Cherif (نور الصباح الشريف)",
      "classe": "3eco"
    },
    {
      "id": 208,
      "username": "hiba.cherif.listed",
      "full_name": "Hiba Cherif (هبة شريف)",
      "classe": "3eco"
    },
    {
      "id": 209,
      "username": "hiba.meskini.listed",
      "full_name": "Hiba Meskini (هبة مسكيني)",
      "classe": "3eco"
    },
    {
      "id": 210,
      "username": "wassima.dhouioui.listed",
      "full_name": "Wassima Dhouioui (وسيمة ضويوي)",
      "classe": "3eco"
    },
    {
      "id": 211,
      "username": "yassine.belhoudi.listed",
      "full_name": "Yassine Belhoudi (ياسين بلحودي)",
      "classe": "3eco"
    },
    {
      "id": 212,
      "username": "youssef.hamdi.listed",
      "full_name": "Youssef Hamdi (يوسف حمدي)",
      "classe": "3eco"
    },
    {
      "id": 213,
      "username": "youssef.adali.listed",
      "full_name": "Youssef Adali (يوسف عدالي)",
      "classe": "3eco"
    },
    {
      "id": 214,
      "username": "zeineb.dhouioui.listed.27",
      "full_name": "Zeineb عبد الرزاق Dhouioui (زينب عبد الرزاق ضويوي)",
      "classe": "3eco"
    }
  ],
  "4 science": [
    {
      "id": 132,
      "username": "ibrahim.nasri.listeb",
      "full_name": "Ibrahim Nasri (إبراهيم نصري)",
      "classe": "4 science"
    },
    {
      "id": 133,
      "username": "adem.dhouioui.listeb",
      "full_name": "Adem Dhouioui (آدم ضويوي)",
      "classe": "4 science"
    },
    {
      "id": 134,
      "username": "amani.helali.listeb",
      "full_name": "Amani Helali (أماني هلالي)",
      "classe": "4 science"
    },
    {
      "id": 135,
      "username": "anes.nasri.listeb",
      "full_name": "Anes Nasri (أنس نصري)",
      "classe": "4 science"
    },
    {
      "id": 136,
      "username": "rania.nasri.listeb",
      "full_name": "Rania Nasri (رانية نصري)",
      "classe": "4 science"
    },
    {
      "id": 137,
      "username": "rahma.nasri.listeb",
      "full_name": "Rahma Nasri (رحمة نصري)",
      "classe": "4 science"
    },
    {
      "id": 138,
      "username": "rym.rahmani.listeb",
      "full_name": "Rym Rahmani (ريم رحماني)",
      "classe": "4 science"
    },
    {
      "id": 139,
      "username": "rayan.dridi.listeb",
      "full_name": "Rayan Dridi (ريان الدريدي)",
      "classe": "4 science"
    },
    {
      "id": 140,
      "username": "zeineb.tlili.listeb",
      "full_name": "Zeineb Tlili (زينب تليلي)",
      "classe": "4 science"
    },
    {
      "id": 141,
      "username": "sahar.chihaoui.listeb",
      "full_name": "Sahar Chihaoui (سحر شيحاوي)",
      "classe": "4 science"
    },
    {
      "id": 142,
      "username": "sirine.hamdi.listeb",
      "full_name": "Sirine Hamdi (سيرين حمدي)",
      "classe": "4 science"
    },
    {
      "id": 143,
      "username": "tarek.khemari.listeb",
      "full_name": "Tarek Khemari (طارق خماري)",
      "classe": "4 science"
    },
    {
      "id": 144,
      "username": "kawthar.belhoudi.listeb",
      "full_name": "Kawthar Belhoudi (كوثر بلحودي)",
      "classe": "4 science"
    },
    {
      "id": 145,
      "username": "mohamed.dhouioui.listeb",
      "full_name": "Mohamed Dhouioui (محمد ضويوي)",
      "classe": "4 science"
    },
    {
      "id": 146,
      "username": "mohamed.dhouioui.listeb.15",
      "full_name": "Mohamed أمين Dhouioui (محمد أمين ضويوي)",
      "classe": "4 science"
    },
    {
      "id": 147,
      "username": "maram.thabti.listeb",
      "full_name": "Maram Thabti (مرام ثابتي)",
      "classe": "4 science"
    },
    {
      "id": 148,
      "username": "meriem.dhouioui.listeb",
      "full_name": "Meriem Dhouioui (مريم ضويوي)",
      "classe": "4 science"
    },
    {
      "id": 149,
      "username": "maha.khemari.listeb",
      "full_name": "Maha Khemari (مها خماري)",
      "classe": "4 science"
    },
    {
      "id": 150,
      "username": "hadeel.dhouioui.listeb",
      "full_name": "Hadeel Dhouioui (هديل ضويوي)",
      "classe": "4 science"
    },
    {
      "id": 151,
      "username": "hadeel.nasri.listeb",
      "full_name": "Hadeel Nasri (هديل نصري)",
      "classe": "4 science"
    },
    {
      "id": 152,
      "username": "wiem.rahmani.listeb",
      "full_name": "Wiem Rahmani (وئام رحماني)",
      "classe": "4 science"
    }
  ],
  "4eco": [
    {
      "id": 153,
      "username": "ibtissem.mlayki.listec",
      "full_name": "Ibtissem Mlayki (إبتسام ملايكي)",
      "classe": "4eco"
    },
    {
      "id": 154,
      "username": "ibrahim.nasri.listec",
      "full_name": "Ibrahim Nasri (إبراهيم نصري)",
      "classe": "4eco"
    },
    {
      "id": 155,
      "username": "oussama.rahmani.listec",
      "full_name": "Oussama Rahmani (أسامة رحماني)",
      "classe": "4eco"
    },
    {
      "id": 156,
      "username": "islam.nasri.listec",
      "full_name": "Islam Nasri (إسلام نصري)",
      "classe": "4eco"
    },
    {
      "id": 157,
      "username": "asma.dhouioui.listec",
      "full_name": "Asma Dhouioui (أسماء ضويوي)",
      "classe": "4eco"
    },
    {
      "id": 158,
      "username": "amani.belhoudi.listec",
      "full_name": "Amani Belhoudi (أماني بلحودي)",
      "classe": "4eco"
    },
    {
      "id": 159,
      "username": "amani.rahmani.listec",
      "full_name": "Amani Rahmani (أماني رحماني)",
      "classe": "4eco"
    },
    {
      "id": 160,
      "username": "intissar.thabti.listec",
      "full_name": "Intissar Thabti (انتصار ثابتي)",
      "classe": "4eco"
    },
    {
      "id": 161,
      "username": "anis.cherif.listec",
      "full_name": "Anis Cherif (أنيس الشريف)",
      "classe": "4eco"
    },
    {
      "id": 162,
      "username": "aya.omrani.listec",
      "full_name": "Aya Omrani (آية العمراني)",
      "classe": "4eco"
    },
    {
      "id": 163,
      "username": "jaouhar.dhouioui.listec",
      "full_name": "Jaouhar Dhouioui (جوهر ضويوي)",
      "classe": "4eco"
    },
    {
      "id": 164,
      "username": "jihane.chehibi.listec",
      "full_name": "Jihane Chehibi (جيهان شهيبي)",
      "classe": "4eco"
    },
    {
      "id": 165,
      "username": "hamdi.dhouioui.listec",
      "full_name": "Hamdi Dhouioui (حمدي ضويوي)",
      "classe": "4eco"
    },
    {
      "id": 166,
      "username": "rahma.dhouioui.listec",
      "full_name": "Rahma Dhouioui (رحمة ضويوي)",
      "classe": "4eco"
    },
    {
      "id": 167,
      "username": "sahar.chbiti.listec",
      "full_name": "Sahar Chbiti (سحر شبيطي)",
      "classe": "4eco"
    },
    {
      "id": 168,
      "username": "senda.nasraoui.listec",
      "full_name": "Senda Nasraoui (سندة نصراوي)",
      "classe": "4eco"
    },
    {
      "id": 169,
      "username": "siwar.belhoudi.listec",
      "full_name": "Siwar Belhoudi (سوار بلحودي)",
      "classe": "4eco"
    },
    {
      "id": 170,
      "username": "sirine.sebri.listec",
      "full_name": "Sirine Sebri (سيرين سبري)",
      "classe": "4eco"
    },
    {
      "id": 171,
      "username": "chaima.dhouioui.listec",
      "full_name": "Chaima Dhouioui (شيماء ضويوي)",
      "classe": "4eco"
    },
    {
      "id": 172,
      "username": "helali.listec",
      "full_name": "علاء الدين Helali (علاء الدين هلالي)",
      "classe": "4eco"
    },
    {
      "id": 173,
      "username": "alia.meskini.listec",
      "full_name": "Alia Meskini (علية مسكيني)",
      "classe": "4eco"
    },
    {
      "id": 174,
      "username": "omar.khelili.listec",
      "full_name": "Omar Khelili (عمر خليلي)",
      "classe": "4eco"
    },
    {
      "id": 175,
      "username": "ghofrane.fakher.listec",
      "full_name": "Ghofrane Fakher (غفران الفاخر)",
      "classe": "4eco"
    },
    {
      "id": 176,
      "username": "foued.mlouki.listec",
      "full_name": "Foued Mlouki (فؤاد ملوكي)",
      "classe": "4eco"
    },
    {
      "id": 177,
      "username": "fatma.fakher.listec",
      "full_name": "Fatma Fakher (فاطمة الفاخر)",
      "classe": "4eco"
    },
    {
      "id": 178,
      "username": "mohamed.tounsi.listec",
      "full_name": "Mohamed أمين Tounsi (محمد أمين تونسي)",
      "classe": "4eco"
    },
    {
      "id": 179,
      "username": "mohamed.khemari.listec",
      "full_name": "Mohamed أمين Khemari (محمد أمين خماري)",
      "classe": "4eco"
    },
    {
      "id": 180,
      "username": "mohamed.rayan.rahmani.listec",
      "full_name": "Mohamed Rayan Rahmani (محمد ريان رحماني)",
      "classe": "4eco"
    },
    {
      "id": 181,
      "username": "mohamed.aziz.rahmani.listec",
      "full_name": "Mohamed Aziz Rahmani (محمد عزيز الرحماني)",
      "classe": "4eco"
    },
    {
      "id": 182,
      "username": "mohamed.yassine.majri.listec",
      "full_name": "Mohamed Yassine Majri (محمد ياسين ماجري)",
      "classe": "4eco"
    },
    {
      "id": 183,
      "username": "mayssa.nasri.listec",
      "full_name": "Mayssa Nasri (ميساء نصري)",
      "classe": "4eco"
    },
    {
      "id": 184,
      "username": "wissal.cherif.listec",
      "full_name": "Wissal Cherif (وصال شريف)",
      "classe": "4eco"
    },
    {
      "id": 185,
      "username": "thabti.listec",
      "full_name": "Thabti (ثابتي)",
      "classe": "4eco"
    },
    {
      "id": 186,
      "username": "thamer.helali.listec",
      "full_name": "Thamer Helali (ثامر هلالي)",
      "classe": "4eco"
    },
    {
      "id": 187,
      "username": "slim.rahmani.listec",
      "full_name": "Slim Rahmani (سليم رحماني)",
      "classe": "4eco"
    }
  ]
};

export async function onRequest(context) {
  return handleRequest(context);
}
export async function onRequestGet(context) {
  return handleRequest(context);
}
async function handleRequest(context) {
  const url = new URL(context.request.url);
  const classe = url.searchParams.get('classe');

  if (!classe) {
    return new Response(JSON.stringify({ students: [] }), {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }

  // Look up students for the requested class
  const students = ALL_STUDENTS[classe] || [];

  return new Response(JSON.stringify({ students }), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Access-Control-Allow-Origin': '*'
    }
  });
}
