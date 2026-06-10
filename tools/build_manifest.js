// Собирает манифест Pinterest-пинов для публикации в Buffer + расписание.
// Запуск: node tools/build_manifest.js  → пишет ../pinterest-pins-manifest.json
const fs=require('fs'), path=require('path');

const RAW='https://raw.githubusercontent.com/listosha/Insta/main';
const BOARD={ name:'Быстрое сохранение', serviceId:'1084523222707156579' };
const LINK={ iron:'https://app.listoshenkov.ru/?section=freeguide_protokol-zhelezo-8-nedel',
             hair:'https://app.listoshenkov.ru/?section=freeguide_protokol-volosy-3-mesyaca' };
const artUrl=s=>`https://listoshenkov.ru/zametki/${s}/?utm_source=pinterest&utm_medium=social&utm_campaign=zametki&utm_content=${s}`;

// Гайды → один из двух гейтов. Картинки в images/pins/. Порядок чередует железо/волосы.
const GUIDES=[
  {slug:'zhelezo-produkty',   gate:'iron', title:'10 продуктов, где железа больше, чем в гречке', items:['Говяжья печень','Моллюски и устрицы','Чечевица','Тыквенные семечки','Говядина','Шпинат','Белая фасоль','Киноа','Тёмный шоколад','Курага']},
  {slug:'volosy-prichiny',    gate:'hair', title:'Волосы сыплются: 6 дефицитов, которые виноваты', items:['Низкий ферритин','Витамин D','Цинк','Щитовидка (ТТГ, Т4св)','Белок','B12 и фолаты']},
  {slug:'zhelezo-priznaki',   gate:'iron', title:'7 признаков скрытого дефицита железа', items:['Выпадение волос','Ломкие ногти','Усталость к обеду','Одышка на лестнице','Тяга грызть лёд','Бледность','Холодные руки и ноги']},
  {slug:'volosy-produkty',    gate:'hair', title:'6 продуктов для густоты волос', items:['Печень и красное мясо','Яйца','Жирная рыба','Тыквенные семечки','Греческий йогурт','Орехи и бобовые']},
  {slug:'zhelezo-analizy',    gate:'iron', title:'5 анализов, чтобы проверить запасы железа', items:['Ферритин','Сывороточное железо','ОЖСС','Трансферрин','Общий анализ крови']},
  {slug:'volosy-analizy',     gate:'hair', title:'Волосы лезут? 5 анализов сделать до трихолога', items:['Ферритин','Витамин D','ТТГ и Т4 свободный','Цинк','Белок и B12']},
  {slug:'zhelezo-usvoenie',   gate:'iron', title:'6 ошибок, из-за которых железо не усваивается', items:['Чай и кофе после еды','Кальций с железом','Мало витамина C','Воспаление в ЖКТ','Дефицит белка','Антациды и ИПП']},
  {slug:'volosy-oshibki',     gate:'hair', title:'Уход не помогает: 5 ошибок при выпадении волос', items:['Лечите шампунем, а не дефицит','Жёсткие диеты','Игнор щитовидки','Стресс','Ждёте результат за неделю']},
  {slug:'zhelezo-rastitelnoe',gate:'iron', title:'Железо без мяса: 8 растительных источников', items:['Чечевица','Тофу и темпе','Тыквенные семечки','Шпинат','Киноа','Нут','Курага','Тёмный шоколад']},
  {slug:'zhelezo-pomoshniki', gate:'iron', title:'Что помогает железу усвоиться: 6 союзников', items:['Витамин C','Мясо рядом с растительным железом','Замачивание круп','Лечить ЖКТ','Белок','Развести с кальцием и чаем']}
];
// Статьи → конкретная заметка с UTM. Картинки в images/pins-articles/.
const ARTICLES=[
  {slug:'kortizol',      title:'5 признаков, что кортизол сбит — а анализ в норме', items:['Еле встаёшь по утрам','Не уснуть до двух ночи','Провал сил после обеда','Тянет на солёное','Просыпаешься разбитой']},
  {slug:'schitovidka',   title:'ТТГ в норме, а вы как в спячке: 6 сигналов щитовидки', items:['Мёрзнете в тепле','Вес растёт','Волосы редеют','Усталость и туман','Сухая кожа','Запоры и отёки']},
  {slug:'son-3-nochi',   title:'Просыпаешься в 3 ночи? 5 причин — и это не голова', items:['Сахарные качели','Скачок кортизола','Поздний ужин','Алкоголь','Падение прогестерона']},
  {slug:'ves',           title:'Вес стоит на дефиците? 3 гормона держат жир под замком', items:['Инсулин','Кортизол','Щитовидка']},
  {slug:'pms',           title:'ПМС всё тяжелее? 5 сигналов перекоса эстроген/прогестерон', items:['Болит грудь','Отёки 2-й фазы','Тревога','Бессонница','Срывы на сладкое']},
  {slug:'perimenopauza', title:'Перименопауза после 40: 6 ранних признаков', items:['Нерегулярный цикл','Рваный сон','Растёт вес','Тревожность','Приливы-предвестники','Падает прогестерон']},
  {slug:'trevoga',       title:'Тревога — не характер: 5 телесных причин', items:['Стресс и кортизол','Кишечник','Дефицит магния и B6','Сахарные качели','Мало белка']},
  {slug:'kishechnik',    title:'Кишечник рулит гормонами: 5 связей, о которых молчат', items:['Выводит эстроген','Сырьё для серотонина','Усвоение железа и D','Конверсия щитовидки','Воспаление']},
  {slug:'holesterin',    title:'Холестерин повышен? 5 фактов до статинов', items:['Сырьё для гормонов','Роль печени','Связь с щитовидкой','Холестерин и ПМС','Цифра — не приговор']}
];

const clip=(s,n)=>s.length<=n?s:s.slice(0,n-1).trimEnd()+'…';
function entry(p,type){
  const isGuide=type==='guide';
  const img=`${RAW}/${isGuide?'images/pins':'images/pins-articles'}/${p.slug}.png`;
  const link=isGuide?LINK[p.gate]:artUrl(p.slug);
  const cta=isGuide?'Полный гайд — бесплатно по ссылке.':'Подробный разбор — в статье по ссылке.';
  const desc=clip(`${p.title}. ${p.items.join(' · ')}. ${cta}`,480);
  return { slug:p.slug, type, gate:isGuide?p.gate:undefined, image:img,
           title:clip(p.title,100), description:desc, link, board:BOARD };
}

// Расписание: с завтра, 2/день — статья 10:00 + гайд 21:00 (МСК).
function dateStr(i){const d=new Date(Date.UTC(2026,5,12)); d.setUTCDate(d.getUTCDate()+i); return d.toISOString().slice(0,10);}
const pins=[];
const maxDays=Math.max(ARTICLES.length,GUIDES.length);
for(let i=0;i<maxDays;i++){
  const date=dateStr(i);
  if(ARTICLES[i]) pins.push({...entry(ARTICLES[i],'article'), date, time:'10:00', tz:'Europe/Moscow', scheduled_at:`${date}T10:00:00+03:00`});
  if(GUIDES[i])   pins.push({...entry(GUIDES[i],'guide'),     date, time:'21:00', tz:'Europe/Moscow', scheduled_at:`${date}T21:00:00+03:00`});
}

const manifest={
  channel:'pinterest', publisher:'buffer', account:'listosha0484',
  generated_for:'Buffer (создание пинов) + витрина календаря',
  board:BOARD,
  schedule:{ start:dateStr(0), per_day:2, slots:{article:'10:00 Europe/Moscow', guide:'21:00 Europe/Moscow'} },
  counts:{ total:pins.length, guides:GUIDES.length, articles:ARTICLES.length },
  pins
};
const out=path.resolve(__dirname,'..','pinterest-pins-manifest.json');
fs.writeFileSync(out, JSON.stringify(manifest,null,2)+'\n');
console.log(`OK: ${pins.length} пинов → ${out}`);
console.log(`Период: ${dateStr(0)} … ${dateStr(maxDays-1)}`);
