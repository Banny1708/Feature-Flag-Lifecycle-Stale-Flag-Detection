package main

const GoEvalFlag = true

func render() int {
	if GoEvalFlag {
		return 1
	}
	return 0
}
