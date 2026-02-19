import path from "node:path"
import { defineConfig } from "prisma/config"

export default defineConfig({
  schema: "./prisma/schema.prisma",
  datasource: {
    url: `file:${path.join(process.cwd(), "prisma", "dev.db")}`,
  },
})
