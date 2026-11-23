raise "Unexpected sprintf result" unless sprintf("%d", 42) == "42"

def expect_missing
  yield
  false
rescue NoMethodError
  true
end

raise "p was available" unless expect_missing { p 42 }
raise "print was available" unless expect_missing { print 42 }
raise "puts was available" unless expect_missing { puts 42 }
raise "printf was available" unless expect_missing { printf "%d", 42 }
