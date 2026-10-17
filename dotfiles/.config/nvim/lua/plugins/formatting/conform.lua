local options = {
    formatters_by_ft = {
        lua = { "stylua" },
        css = { "prettier" },
        html = { "prettier" },
        typescript = { "prettier" },
        typescriptreact = { "prettier" },
        javascript = { "prettier" },
        javascriptreact = { "prettier" },
        go = { "goimports-reviser", "gofumpt" },
        sql = { "sqlfmt" },
        cpp = { "clang-format" },
        python = { "black" },
    },

    format_on_save = {
        timeout_ms = 5000,
        lsp_fallback = true,
    },

    formatters = {
        ["clang-format"] = {
            command = "xcrun",
            prepend_args = { "clang-format" },
        },
        black = {
            prepend_args = { "--fast" },
        },
    },
}

return {
    "stevearc/conform.nvim",
    event = { "BufWritePre" },
    cmd = { "ConformInfo" },
    opts = options,
}
