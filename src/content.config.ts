import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    publishDate: z.date(),
    updatedDate: z.date().optional(),
    category: z.string(),
    heroImage: z.string().optional(),
    heroImageAlt: z.string().optional(),
    heroImageCreditName: z.string().optional(),
    heroImageCreditUrl: z.string().optional(),
    // 'guide'  — decision guide: teaches the selection criteria and lays the
    //            options out in a spec table. No ranking, no "best pick", no
    //            verdict, so the page's purpose is reference rather than
    //            recommendation.
    // 'comparison' — the original ranked product-card format. Legacy; posts
    //            still on it are being converted.
    format: z.enum(['guide', 'comparison']).default('comparison'),

    // Spec table for `format: guide`. Deliberately carries no price column:
    // PickLoot has no live pricing feed, and a hardcoded figure goes stale and
    // breaks affiliate-program rules. `tier` gives the rough price band instead.
    specs: z
      .object({
        columns: z.array(z.string()),
        options: z.array(
          z.object({
            name: z.string(),
            tier: z.enum(['Budget', 'Mid-range', 'Premium']).optional(),
            amazonUrl: z.string().optional(),
            values: z.array(z.string()),
            fitsWhen: z.string().optional(),
          })
        ),
      })
      .optional(),

    products: z
      .array(
        z.object({
          name: z.string(),
          amazonUrl: z.string(),
          price: z.string().optional(),
          image: z.string().optional(),
          pros: z.array(z.string()).optional(),
          cons: z.array(z.string()).optional(),
        })
      )
      .optional(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { posts };
