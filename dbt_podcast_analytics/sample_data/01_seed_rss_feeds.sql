CREATE OR REPLACE TABLE `your-gcp-project.bronze.rss_feeds` AS
SELECT 'https://feeds.example.com/tech-talk-daily' AS feed_url,
       'Tech Talk Daily' AS title,
       'A daily podcast about technology, software engineering, and the future of computing, with interviews and deep dives.' AS description,
       DATE '2024-01-15' AS published_date,
       '<rss><channel><title>Tech Talk Daily</title><language>en</language><category>Technology</category><itunes:author>Jane Developer</itunes:author><link>https://techtalk.example.com</link><itunes:image href="https://techtalk.example.com/art.jpg"/><itunes:explicit>false</itunes:explicit><itunes:episode>125</itunes:episode></channel></rss>' AS raw_content,
       TIMESTAMP '2024-01-15 10:00:00 UTC' AS ingestion_timestamp,
       'rss' AS source_type
UNION ALL
SELECT 'https://feeds.example.com/history-unpacked',
       'History Unpacked',
       'Long-form storytelling that unpacks pivotal moments in world history, one episode at a time.',
       DATE '2024-02-02',
       '<rss><channel><title>History Unpacked</title><language>en-GB</language><category>History</category><itunes:author>Marcus Reed</itunes:author><link>https://historyunpacked.example.com</link><itunes:image href="https://historyunpacked.example.com/cover.png"/><itunes:explicit>false</itunes:explicit><itunes:episode>88</itunes:episode></channel></rss>',
       TIMESTAMP '2024-02-02 08:30:00 UTC',
       'rss'
UNION ALL
SELECT 'https://feeds.example.com/true-crime-files',
       'True Crime Files',
       'Investigative true-crime cases told with original reporting and expert interviews.',
       DATE '2024-03-10',
       '<rss><channel><title>True Crime Files</title><language>en</language><category>True Crime</category><itunes:author>Dana Cole</itunes:author><link>https://truecrimefiles.example.com</link><itunes:image href="https://truecrimefiles.example.com/art.jpg"/><itunes:explicit>true</itunes:explicit><itunes:episode>210</itunes:episode></channel></rss>',
       TIMESTAMP '2024-03-10 14:15:00 UTC',
       'rss'
UNION ALL
SELECT 'https://feeds.example.com/startup-stories',
       'Startup Stories',
       'Founders share the real, unfiltered journeys behind building their companies from zero.',
       DATE '2024-04-05',
       '<rss><channel><title>Startup Stories</title><language>en</language><category>Business</category><itunes:author>Priya Nair</itunes:author><link>https://startupstories.example.com</link><itunes:image href="https://startupstories.example.com/logo.jpg"/><itunes:explicit>false</itunes:explicit><itunes:episode>57</itunes:episode></channel></rss>',
       TIMESTAMP '2024-04-05 09:45:00 UTC',
       'rss';
