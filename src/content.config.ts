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
